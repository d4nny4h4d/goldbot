"""Backtest GoldBot ITF strategy on 5 target dates with MT5-matching indicators.

Strategy: Intraday Trend Following (ITF)
  - Timeframe: M15
  - Direction: EMA(44) filter (above = long only, below = short only)
  - Entry: RSI(14) in 40-60 neutral zone AND turning in trend direction
  - ADX(14) >= 25 required
  - SL: 1.65 x ATR(14), TP: 3.0 x ATR(14)
  - Trailing SL: 1.65 x ATR (only moves favorably)
  - Hard exit: 20:00 UTC, no new trades after 19:00 UTC
  - Risk: 2% of equity, max 2 positions, max 1 same direction
  - Daily loss limit: 3%

Indicators:
  - RSI(14): Wilder's smoothing (alpha=1/period)
  - ATR(14): Wilder's smoothing (alpha=1/period)
  - ADX(14): span-based EMA (ewm(span=period))
  - EMA(44): standard EMA (ewm(span=period))
"""

import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Use GoldBot's env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
mt5.initialize(
    path=os.getenv("MT5_PATH"),
    login=int(os.getenv("MT5_LOGIN")),
    password=os.getenv("MT5_PASSWORD"),
    server=os.getenv("MT5_SERVER"),
)
sym = os.getenv("MT5_SYMBOL", "XAUUSDm")

# Pull M15 data - need enough for warmup
start = datetime(2026, 2, 15, 0, 0, tzinfo=timezone.utc)  # extra warmup for EMA(44)
end = datetime(2026, 3, 17, 23, 59, tzinfo=timezone.utc)
rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, start, end)
if rates is None or len(rates) == 0:
    print("No M15 data returned!")
    print(mt5.last_error())
    mt5.shutdown()
    sys.exit(1)

df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
print(f"M15 Data: {df['time'].iloc[0]} to {df['time'].iloc[-1]} ({len(df)} bars)")

close = df["close"]

# --- EMA(44) - standard EMA ---
df["ema44"] = close.ewm(span=44, adjust=False).mean()

# --- RSI(14) - Wilder's smoothing ---
delta = close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df["rsi"] = 100 - (100 / (1 + rs))
df["rsi_prev"] = df["rsi"].shift(1)

# --- ATR(14) - Wilder's smoothing ---
tr = np.maximum(
    df["high"] - df["low"],
    np.maximum(
        abs(df["high"] - df["close"].shift(1)),
        abs(df["low"] - df["close"].shift(1)),
    ),
)
df["atr"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

# --- ADX(14) - span-based EMA (matches MT5) ---
plus_dm = df["high"].diff()
minus_dm = -df["low"].diff()
plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
tr2 = pd.concat(
    [
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ],
    axis=1,
).max(axis=1)
atr2 = tr2.ewm(span=14, adjust=False).mean()
plus_di = 100 * (plus_dm.ewm(span=14, adjust=False).mean() / atr2)
minus_di = 100 * (minus_dm.ewm(span=14, adjust=False).mean() / atr2)
dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
df["adx"] = dx.ewm(span=14, adjust=False).mean()

# Strategy parameters
EMA_PERIOD = 44
RSI_LOW = 40
RSI_HIGH = 60
MIN_ADX = 25
SL_ATR_MULT = 1.65
TP_ATR_MULT = 3.0
TRAIL_ATR_MULT = 1.65
HARD_EXIT_HOUR = 20
NO_NEW_TRADES_HOUR = 19
RISK_PCT = 0.02
MAX_POSITIONS = 2
MAX_SAME_DIR = 1
DAILY_LOSS_LIMIT = 0.03

target_dates = [2, 4, 5, 12, 13]
point = 0.001
starting_equity = 500.0  # GoldBot starts with $500

all_results = {}

for day in target_dates:
    day_df = df[(df["time"].dt.month == 3) & (df["time"].dt.day == day)].copy()
    if len(day_df) == 0:
        print(f"March {day}: NO DATA")
        continue

    print(f"========== MARCH {day} ==========")
    print(
        f"M15 Bars: {len(day_df)} | "
        f"Range: {day_df['time'].iloc[0].strftime('%H:%M')} - "
        f"{day_df['time'].iloc[-1].strftime('%H:%M')}"
    )

    # Track open positions and daily P&L
    open_positions = []  # list of dicts
    closed_trades = []
    equity = starting_equity
    daily_start_equity = starting_equity
    last_signal_time = None

    for i in range(len(day_df)):
        idx = day_df.index[i]
        row = df.loc[idx]
        current_time = row["time"]
        current_hour = current_time.hour
        current_min = current_time.minute

        if (
            pd.isna(row["adx"])
            or pd.isna(row["rsi"])
            or pd.isna(row["atr"])
            or pd.isna(row["ema44"])
            or pd.isna(row["rsi_prev"])
        ):
            continue

        # --- Hard exit at 20:00 UTC ---
        if current_hour >= HARD_EXIT_HOUR:
            for pos in open_positions[:]:
                if pos["dir"] == "BUY":
                    pnl_pts = (row["close"] - pos["entry"]) / point
                else:
                    pnl_pts = (pos["entry"] - row["close"]) / point

                sl_dist_usd = abs(pos["entry"] - pos["sl"]) * 100
                lot_size = (pos["equity_at_entry"] * RISK_PCT) / sl_dist_usd if sl_dist_usd > 0 else 0.01
                lot_size = max(0.01, min(0.10, round(lot_size, 2)))
                pnl_usd = pnl_pts * point * 100 * lot_size

                closed_trades.append({
                    **pos,
                    "result": "HARD_EXIT",
                    "exit_price": row["close"],
                    "exit_time": current_time,
                    "pnl_pts": pnl_pts,
                    "lots": lot_size,
                    "pnl_usd": pnl_usd,
                })
                equity += pnl_usd

            open_positions.clear()
            continue

        # --- Update trailing stops on open positions ---
        for pos in open_positions:
            trail_dist = TRAIL_ATR_MULT * row["atr"]
            if pos["dir"] == "BUY":
                new_sl = row["close"] - trail_dist
                if new_sl > pos["sl"] and new_sl < row["close"]:
                    pos["sl"] = new_sl
            else:
                new_sl = row["close"] + trail_dist
                if pos["sl"] == 0 or (new_sl < pos["sl"] and new_sl > row["close"]):
                    pos["sl"] = new_sl

        # --- Check SL/TP on open positions ---
        for pos in open_positions[:]:
            hit_sl = False
            hit_tp = False

            if pos["dir"] == "BUY":
                if row["low"] <= pos["sl"]:
                    hit_sl = True
                elif row["high"] >= pos["tp"]:
                    hit_tp = True
            else:
                if row["high"] >= pos["sl"]:
                    hit_sl = True
                elif row["low"] <= pos["tp"]:
                    hit_tp = True

            if hit_sl or hit_tp:
                exit_price = pos["sl"] if hit_sl else pos["tp"]
                if pos["dir"] == "BUY":
                    pnl_pts = (exit_price - pos["entry"]) / point
                else:
                    pnl_pts = (pos["entry"] - exit_price) / point

                sl_dist_usd = abs(pos["entry"] - pos["original_sl"]) * 100
                lot_size = (pos["equity_at_entry"] * RISK_PCT) / sl_dist_usd if sl_dist_usd > 0 else 0.01
                lot_size = max(0.01, min(0.10, round(lot_size, 2)))
                pnl_usd = pnl_pts * point * 100 * lot_size

                result = "SL" if hit_sl else "TP"
                closed_trades.append({
                    **pos,
                    "result": result,
                    "exit_price": exit_price,
                    "exit_time": current_time,
                    "pnl_pts": pnl_pts,
                    "lots": lot_size,
                    "pnl_usd": pnl_usd,
                })
                equity += pnl_usd
                open_positions.remove(pos)

        # --- Daily loss limit check ---
        daily_pnl_pct = (equity - daily_start_equity) / daily_start_equity
        if daily_pnl_pct <= -DAILY_LOSS_LIMIT:
            continue  # stop trading for the day

        # --- No new trades after 19:00 UTC ---
        if current_hour >= NO_NEW_TRADES_HOUR:
            continue

        # --- Max positions check ---
        if len(open_positions) >= MAX_POSITIONS:
            continue

        # --- ADX minimum filter ---
        if row["adx"] < MIN_ADX:
            continue

        # --- Avoid duplicate signals on same candle ---
        if last_signal_time == current_time:
            continue

        # --- Signal generation ---
        direction = None

        # Bullish: price above EMA, RSI in neutral zone, RSI turning up
        if row["close"] > row["ema44"]:
            if RSI_LOW <= row["rsi"] <= RSI_HIGH:
                if row["rsi"] > row["rsi_prev"]:
                    # Check max same direction
                    long_count = sum(1 for p in open_positions if p["dir"] == "BUY")
                    if long_count < MAX_SAME_DIR:
                        direction = "BUY"

        # Bearish: price below EMA, RSI in neutral zone, RSI turning down
        elif row["close"] < row["ema44"]:
            if RSI_LOW <= row["rsi"] <= RSI_HIGH:
                if row["rsi"] < row["rsi_prev"]:
                    short_count = sum(1 for p in open_positions if p["dir"] == "SELL")
                    if short_count < MAX_SAME_DIR:
                        direction = "SELL"

        if direction is None:
            continue

        # --- Calculate entry, SL, TP ---
        sl_dist = SL_ATR_MULT * row["atr"]
        tp_dist = TP_ATR_MULT * row["atr"]

        if direction == "BUY":
            entry = row["close"]  # use ask in live, close for backtest
            sl = entry - sl_dist
            tp = entry + tp_dist
        else:
            entry = row["close"]
            sl = entry + sl_dist
            tp = entry - tp_dist

        pos_data = {
            "time": current_time,
            "dir": direction,
            "entry": entry,
            "sl": sl,
            "original_sl": sl,
            "tp": tp,
            "rsi": row["rsi"],
            "adx": row["adx"],
            "atr": row["atr"],
            "ema44": row["ema44"],
            "equity_at_entry": equity,
        }
        open_positions.append(pos_data)
        last_signal_time = current_time

    # --- Force close any remaining positions at end of data ---
    if open_positions:
        last_bar = day_df.iloc[-1]
        for pos in open_positions:
            if pos["dir"] == "BUY":
                pnl_pts = (last_bar["close"] - pos["entry"]) / point
            else:
                pnl_pts = (pos["entry"] - last_bar["close"]) / point

            sl_dist_usd = abs(pos["entry"] - pos["original_sl"]) * 100
            lot_size = (pos["equity_at_entry"] * RISK_PCT) / sl_dist_usd if sl_dist_usd > 0 else 0.01
            lot_size = max(0.01, min(0.10, round(lot_size, 2)))
            pnl_usd = pnl_pts * point * 100 * lot_size

            closed_trades.append({
                **pos,
                "result": "EOD",
                "exit_price": last_bar["close"],
                "exit_time": last_bar["time"],
                "pnl_pts": pnl_pts,
                "lots": lot_size,
                "pnl_usd": pnl_usd,
            })
        open_positions.clear()

    # --- Print results ---
    total_trades = len(closed_trades)
    wins = sum(1 for t in closed_trades if t["pnl_pts"] > 0)
    losses = total_trades - wins
    total_pts = sum(t["pnl_pts"] for t in closed_trades)
    total_usd = sum(t["pnl_usd"] for t in closed_trades)
    wr = wins / total_trades * 100 if total_trades > 0 else 0

    print(
        f"  GoldBot ITF: {total_trades} trades, {wins}W/{losses}L, "
        f"WR={wr:.0f}%, {total_pts:+.0f} pts, "
        f"~USD {total_usd:+.2f} ({total_usd / starting_equity * 100:+.2f}%)"
    )
    for t in closed_trades:
        et = t["exit_time"].strftime("%H:%M") if t.get("exit_time") else "??"
        trail_info = ""
        if t["sl"] != t["original_sl"]:
            trail_info = f" [trailed from {t['original_sl']:.2f}]"
        print(
            f"    {t['time'].strftime('%H:%M')} {t['dir']} "
            f"@ {t['entry']:.2f} SL={t['original_sl']:.2f} TP={t['tp']:.2f} | "
            f"RSI={t['rsi']:.1f} ADX={t['adx']:.1f} EMA={t['ema44']:.2f} | "
            f"{t['result']} @ {t['exit_price']:.2f} ({et}){trail_info} | "
            f"{t['pnl_pts']:+.0f}pts {t['lots']:.2f}L "
            f"USD{t['pnl_usd']:+.2f}"
        )

    all_results[day] = {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "pts": total_pts,
        "usd": total_usd,
        "wr": wr,
    }
    print()

# Grand summary
print("=" * 75)
print("GOLDBOT ITF - GRAND SUMMARY (M15, corrected indicators)")
print("=" * 75)
print(
    f"{'Date':>10} {'Trades':>7} {'Wins':>5} {'Losses':>7} "
    f"{'Points':>8} {'USD':>10} {'WR':>6}"
)
for day in target_dates:
    if day in all_results:
        r = all_results[day]
        print(
            f"  Mar {day:>2}  {r['trades']:>7} {r['wins']:>5} "
            f"{r['losses']:>7} {r['pts']:>+8.0f} {r['usd']:>+10.2f} "
            f"{r['wr']:>5.0f}%"
        )

total_t = sum(r.get("trades", 0) for r in all_results.values())
total_w = sum(r.get("wins", 0) for r in all_results.values())
total_l = sum(r.get("losses", 0) for r in all_results.values())
total_p = sum(r.get("pts", 0) for r in all_results.values())
total_u = sum(r.get("usd", 0) for r in all_results.values())
wr = total_w / total_t * 100 if total_t > 0 else 0
print()
print(
    f"TOTAL: {total_t} trades, {total_w}W/{total_l}L, "
    f"WR={wr:.0f}%, {total_p:+.0f}pts, "
    f"USD {total_u:+.2f} ({total_u / starting_equity * 100:+.2f}%)"
)

mt5.shutdown()
