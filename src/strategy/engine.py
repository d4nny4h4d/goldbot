"""Strategy engine — orchestrates signal generation, risk checks, and order execution."""

import logging
from datetime import datetime, timezone

import yaml

from src.data.market_feed import MarketFeed
from src.data.regime_detector import RegimeDetector, MarketRegime
from src.db.database import Database
from src.execution.mt5_executor import MT5Executor
from src.risk.manager import RiskManager
from src.strategy.base_strategy import BaseStrategy, SignalDirection
from src.strategy.itf_strategy import IntradayTrendFollowing

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Central orchestrator: poll strategies → check risk → execute orders → log trades."""

    def __init__(
        self,
        feed: MarketFeed,
        executor: MT5Executor,
        risk_manager: RiskManager,
        database: Database,
        config_path: str = "config/strategies.yaml",
    ):
        self.feed = feed
        self.executor = executor
        self.risk = risk_manager
        self.db = database
        self.regime = RegimeDetector(config_path)

        cfg = self._load_config(config_path)
        self.strategies: list[BaseStrategy] = []

        # Initialize enabled strategies
        if cfg.get("intraday_trend_following", {}).get("enabled"):
            itf = IntradayTrendFollowing(cfg["intraday_trend_following"])
            # Inject feed reference so ITF can fetch HTF candles for trend filter
            itf._feed = feed
            self.strategies.append(itf)
            logger.info("Strategy loaded: Intraday Trend Following (ITF)")

        # Future strategies will be added here as account grows:
        # if cfg.get("london_breakout", {}).get("enabled"):
        #     self.strategies.append(LondonBreakout(cfg["london_breakout"]))
        # if cfg.get("ny_opening_range_breakout", {}).get("enabled"):
        #     self.strategies.append(NYOpeningRangeBreakout(cfg["ny_opening_range_breakout"]))

        logger.info("Engine initialized with %d active strategies", len(self.strategies))

    @staticmethod
    def _load_config(path: str) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    # ── Main tick loop ───────────────────────────────────────────────────────

    def tick(self):
        """Called every check_interval_seconds. Main trading loop iteration."""
        if not self.feed.ensure_connected():
            logger.error("MT5 not connected — skipping tick")
            return

        # Get current market data
        tick = self.feed.get_tick()
        if tick is None:
            return

        candles = self.feed.get_candles("M15", 200)
        if candles is None or len(candles) < 50:
            return

        account = self.feed.get_account_info()
        if account is None:
            return

        equity = account["equity"]

        # Update risk manager
        self.risk.update_equity_snapshot(equity)

        # Check circuit breakers
        cb_status = self.risk.check_circuit_breakers(equity)
        if not cb_status["can_trade"]:
            logger.warning("Trading halted — circuit breaker active")
            return

        # Detect market regime
        regime = self.regime.detect(candles)

        # Save equity snapshot periodically
        self.db.save_equity_snapshot(
            equity=equity,
            balance=account["balance"],
            unrealized_pnl=account["profit"],
            open_positions=len(self.executor.get_open_positions()),
        )

        # Manage existing positions (trailing stops, time exits)
        self._manage_positions(candles, tick)

        # Check for new signals — return result so main.py can send Telegram alert
        return self._check_signals(candles, tick, equity, regime)

    # ── Signal checking ──────────────────────────────────────────────────────

    def _check_signals(self, candles, tick, equity, regime):
        """Poll each strategy for signals and execute if risk allows."""
        symbol_info = self.feed.get_symbol_info()
        if symbol_info is None:
            return

        for strategy in self.strategies:
            if not strategy.enabled:
                continue

            # Check regime weight — skip if strategy doesn't fit regime
            weight = self.regime.get_strategy_weight(strategy.name, regime)
            if weight < 0.2:
                logger.debug(
                    "Skipping %s — low regime weight (%.2f) in %s market",
                    strategy.name, weight, regime,
                )
                continue

            signal = strategy.generate_signal(candles, tick)
            if signal is None:
                continue

            # Risk check
            allowed, reason = self.risk.can_open_trade(signal.direction.value, equity)
            if not allowed:
                logger.info("Signal rejected by risk manager: %s", reason)
                continue

            # Calculate position size
            effective_risk = self.risk.get_effective_risk_pct(equity)
            lots = self.risk.calculate_lot_size(
                equity=equity,
                sl_distance_price=signal.sl_distance,
                symbol_info=symbol_info,
                risk_override_pct=effective_risk if effective_risk != self.risk.risk_per_trade_pct else None,
            )

            if lots <= 0:
                logger.warning("Calculated lot size is 0 — skipping trade")
                continue

            # Execute the trade
            result = self.executor.open_trade(
                direction=signal.direction.value,
                lots=lots,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                comment=f"GB_{signal.strategy_name}",
            )

            if result:
                # Log to database
                self.db.log_trade_open(
                    ticket=result["ticket"],
                    symbol=result["symbol"],
                    direction=result["direction"],
                    lots=lots,
                    entry_price=result["entry_price"],
                    sl=signal.sl_price,
                    tp=signal.tp_price,
                    strategy=signal.strategy_name,
                    equity_at_entry=equity,
                    comment=signal.reason,
                )

                logger.info(
                    "TRADE EXECUTED: %s %s %.2f lots @ %.2f | SL: %.2f | TP: %.2f | %s",
                    signal.direction.value.upper(), self.feed.symbol,
                    lots, result["entry_price"], signal.sl_price,
                    signal.tp_price, signal.strategy_name,
                )

                # Return signal info for alerts
                return {
                    "type": "trade_opened",
                    "signal": signal,
                    "result": result,
                    "lots": lots,
                    "risk_pct": effective_risk,
                    "regime": regime,
                }

        return None

    # ── Position management ──────────────────────────────────────────────────

    def _manage_positions(self, candles, tick):
        """Check open positions for trailing stops and time-based exits."""
        positions = self.executor.get_open_positions()

        for pos in positions:
            # Skip non-bot positions
            if not pos.get("comment", "").startswith("GB_"):
                continue

            strategy_name = pos["comment"].replace("GB_", "")
            strategy = self._get_strategy(strategy_name)
            if strategy is None:
                continue

            # Check time exit
            if strategy.should_close(pos, candles, tick):
                self.executor.close_trade(pos["ticket"], comment="GB_time_exit")
                self._log_position_close(pos)
                continue

            # Update trailing stop (ITF specific)
            if hasattr(strategy, "get_trailing_sl"):
                new_sl = strategy.get_trailing_sl(pos, candles)
                if new_sl is not None:
                    self.executor.modify_sl_tp(pos["ticket"], new_sl=new_sl)
                    logger.info(
                        "TRAILING SL: Ticket %s moved to %.2f",
                        pos["ticket"], new_sl,
                    )

    def _get_strategy(self, name: str) -> BaseStrategy | None:
        for s in self.strategies:
            if s.name == name:
                return s
        return None

    def _log_position_close(self, position: dict):
        """Log a closed position to the database."""
        account = self.feed.get_account_info()
        equity = account["equity"] if account else 0

        self.db.log_trade_close(
            ticket=position["ticket"],
            exit_price=position["current_price"],
            profit_usd=position["profit"],
            equity_at_exit=equity,
        )

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get current engine status for dashboard/alerts."""
        account = self.feed.get_account_info()
        equity = account["equity"] if account else 0

        return {
            "connected": self.feed.is_connected(),
            "equity": equity,
            "regime": self.regime.current_regime,
            "adx": round(self.regime.current_adx, 1),
            "active_strategies": [s.name for s in self.strategies if s.enabled],
            "open_positions": sum(
                1 for p in self.executor.get_open_positions()
                if p.get("comment", "").startswith("GB_")
            ),
            "circuit_breaker": self.risk.check_circuit_breakers(equity),
            "daily_pnl_pct": round(self.risk.get_daily_pnl_pct(equity), 2),
        }
