"""Intraday Trend Following (ITF) — Rank 1 Strategy.

Concept: Uses EMA(44) as direction filter. Enters when RSI(14) pulls back to
the 40-60 neutral zone during a trend, confirming momentum resumption.

Backtest results (2020-2024, $50k):
  - Win rate: 46.2%
  - Profit factor: 1.83
  - Sharpe: 1.58
  - Max drawdown: -10.9%
  - WFO robustness: 0.73
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.strategy.base_strategy import BaseStrategy, SignalDirection, TradeSignal

logger = logging.getLogger(__name__)

_MT5_COMMON_FILES = Path(os.environ.get(
    "MT5_COMMON_FILES",
    os.path.expanduser("~/AppData/Roaming/MetaQuotes/Terminal/Common/Files"),
))
_BRIDGE_STALE_SEC = 30


class IntradayTrendFollowing(BaseStrategy):
    """EMA trend + RSI pullback strategy for XAUUSD."""

    def __init__(self, config: dict):
        super().__init__("ITF", config)
        self.ema_period = config["ema_period"]          # 44
        self.rsi_period = config["rsi_period"]          # 14
        self.rsi_low = config["rsi_low"]                # 40
        self.rsi_high = config["rsi_high"]              # 60
        self.atr_period = config["atr_period"]          # 14
        self.tp_atr_mult = config["tp_atr_mult"]        # 3.0
        self.sl_atr_mult = config["sl_atr_mult"]        # 1.65
        self.hard_exit_utc = config.get("hard_exit_utc", "20:00")
        self.min_adx = config.get("min_adx", 25)

        self._mt5_login = os.environ.get("MT5_LOGIN", "")
        self._last_signal_time = None

    def _read_bridge_adx(self) -> float | None:
        """Read ADX from the shared CSV written by ADXBridge EA."""
        if not self._mt5_login:
            return None
        bridge_file = _MT5_COMMON_FILES / f"adx_{self._mt5_login}.csv"
        if not bridge_file.exists():
            return None
        try:
            mtime = bridge_file.stat().st_mtime
            age = datetime.now(timezone.utc).timestamp() - mtime
            if age > _BRIDGE_STALE_SEC:
                return None
            line = bridge_file.read_text(encoding="utf-16").strip()
            if not line:
                return None
            return float(line.split(",")[1])
        except Exception:
            return None

    # ── Indicators ───────────────────────────────────────────────────────────

    @staticmethod
    def _calc_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _calc_rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        # Wilder's smoothing: alpha=1/period (matches MT5 ATR indicator)
        return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    @staticmethod
    def _wilder_smooth(values: np.ndarray, period: int) -> np.ndarray:
        """Wilder's smoothing matching MT5."""
        result = np.full(len(values), np.nan)
        valid = ~np.isnan(values)
        count = 0
        seed_end = -1
        for i in range(len(values)):
            if valid[i]:
                count += 1
                if count == period:
                    seed_end = i
                    break
            else:
                count = 0
        if seed_end < 0:
            return result
        result[seed_end] = np.mean(values[seed_end - period + 1 : seed_end + 1])
        for i in range(seed_end + 1, len(values)):
            if np.isnan(values[i]):
                result[i] = result[i - 1]
            else:
                result[i] = (result[i - 1] * (period - 1) + values[i]) / period
        return result

    @staticmethod
    def _calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        n = len(high)

        tr = np.full(n, np.nan)
        plus_dm = np.full(n, np.nan)
        minus_dm = np.full(n, np.nan)
        for i in range(1, n):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, hc, lc)
            up = high[i] - high[i - 1]
            dn = low[i - 1] - low[i]
            plus_dm[i] = up if (up > dn and up > 0) else 0.0
            minus_dm[i] = dn if (dn > up and dn > 0) else 0.0

        sm_tr = ITFStrategy._wilder_smooth(tr, period)
        sm_plus = ITFStrategy._wilder_smooth(plus_dm, period)
        sm_minus = ITFStrategy._wilder_smooth(minus_dm, period)

        plus_di = np.where(sm_tr > 0, 100 * sm_plus / sm_tr, 0.0)
        minus_di = np.where(sm_tr > 0, 100 * sm_minus / sm_tr, 0.0)
        di_sum = plus_di + minus_di
        dx = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, np.nan)

        adx = ITFStrategy._wilder_smooth(dx, period)
        return pd.Series(adx, index=df.index)

    # ── Signal generation ────────────────────────────────────────────────────

    def generate_signal(self, candles: pd.DataFrame, tick: dict) -> TradeSignal | None:
        """Check for ITF entry signal on latest candles.

        Entry logic:
        1. Price above EMA(44) → only longs; below → only shorts
        2. RSI(14) in 40-60 neutral zone (pullback)
        3. RSI turning back in trend direction
        4. ADX > min_adx (prefer trending markets)
        """
        if not self.enabled:
            return None

        if len(candles) < max(self.ema_period, self.rsi_period, self.atr_period) + 5:
            return None

        # Check hard exit time — don't open new trades near close
        now_utc = datetime.now(timezone.utc)
        exit_hour, exit_min = map(int, self.hard_exit_utc.split(":"))
        if now_utc.hour >= exit_hour and now_utc.minute >= exit_min:
            return None

        # Don't open trades within 1 hour of hard exit
        if now_utc.hour >= exit_hour - 1:
            return None

        # Avoid duplicate signals on same candle
        last_candle_time = candles.index[-1]
        if self._last_signal_time == last_candle_time:
            return None

        # Calculate indicators
        close = candles["close"]
        ema = self._calc_ema(close, self.ema_period)
        rsi = self._calc_rsi(close, self.rsi_period)
        atr = self._calc_atr(candles, self.atr_period)

        # ADX: prefer MT5 bridge, fallback to calculation
        bridge_adx = self._read_bridge_adx()
        if bridge_adx is not None:
            current_adx = bridge_adx
        else:
            adx = self._calc_adx(candles, 14)
            current_adx = adx.iloc[-1]

        # Get latest values
        current_close = close.iloc[-1]
        current_ema = ema.iloc[-1]
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        current_atr = atr.iloc[-1]

        # ADX filter — only trade in trending conditions
        if np.isnan(current_adx) or current_adx < self.min_adx:
            return None

        direction = SignalDirection.NONE

        # Bullish setup: price above EMA, RSI pulled back to neutral and turning up
        if current_close > current_ema:
            if self.rsi_low <= current_rsi <= self.rsi_high:
                if current_rsi > prev_rsi:  # RSI turning up
                    direction = SignalDirection.BUY

        # Bearish setup: price below EMA, RSI pulled back to neutral and turning down
        elif current_close < current_ema:
            if self.rsi_low <= current_rsi <= self.rsi_high:
                if current_rsi < prev_rsi:  # RSI turning down
                    direction = SignalDirection.SELL

        if direction == SignalDirection.NONE:
            return None

        # Calculate SL and TP
        sl_distance = self.sl_atr_mult * current_atr
        tp_distance = self.tp_atr_mult * current_atr

        if direction == SignalDirection.BUY:
            entry_price = tick["ask"]
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
        else:
            entry_price = tick["bid"]
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance

        self._last_signal_time = last_candle_time

        reason = (
            f"EMA({self.ema_period})={current_ema:.2f} "
            f"RSI({self.rsi_period})={current_rsi:.1f} "
            f"ADX={current_adx:.1f} "
            f"ATR={current_atr:.2f}"
        )

        logger.info(
            "ITF SIGNAL: %s @ %.2f | SL: %.2f (%.2f ATR) | TP: %.2f (%.2f ATR) | %s",
            direction.value.upper(), entry_price, sl_price,
            self.sl_atr_mult, tp_price, self.tp_atr_mult, reason,
        )

        return TradeSignal(
            direction=direction,
            entry_price=entry_price,
            sl_price=round(sl_price, 2),
            tp_price=round(tp_price, 2),
            sl_distance=round(sl_distance, 2),
            strategy_name=self.name,
            reason=reason,
        )

    # ── Position management ──────────────────────────────────────────────────

    def should_close(self, position: dict, candles: pd.DataFrame, tick: dict) -> bool:
        """Check for time-based exit (hard exit at 20:00 UTC)."""
        now_utc = datetime.now(timezone.utc)
        exit_hour, exit_min = map(int, self.hard_exit_utc.split(":"))

        if now_utc.hour >= exit_hour and now_utc.minute >= exit_min:
            logger.info(
                "ITF TIME EXIT: Closing ticket %s at %s UTC",
                position.get("ticket"), now_utc.strftime("%H:%M"),
            )
            return True
        return False

    def get_trailing_sl(self, position: dict, candles: pd.DataFrame) -> float | None:
        """Calculate trailing stop loss based on ATR.

        Returns new SL price if it should be moved, None if no change needed.
        """
        atr = self._calc_atr(candles, self.atr_period)
        current_atr = atr.iloc[-1]
        trail_distance = self.sl_atr_mult * current_atr

        current_price = candles["close"].iloc[-1]
        current_sl = position.get("sl", 0)

        if position["direction"] == "buy":
            new_sl = current_price - trail_distance
            # Only move SL up, never down
            if new_sl > current_sl and new_sl < current_price:
                return round(new_sl, 2)

        elif position["direction"] == "sell":
            new_sl = current_price + trail_distance
            # Only move SL down, never up
            if current_sl == 0 or (new_sl < current_sl and new_sl > current_price):
                return round(new_sl, 2)

        return None
