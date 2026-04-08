import MetaTrader5 as mt5
import pandas as pd

mt5.initialize()

entry = 5175.48
sl = 5164.53
tp = 5195.40
direction = "BUY"

tick = mt5.symbol_info_tick("XAUUSDm")
if tick:
    current_bid = tick.bid
    current_ask = tick.ask

    print(f"Trade signal (from ~16:45 local / 12:45 UTC):")
    print(f"  Direction: {direction}")
    print(f"  Entry:     {entry:.2f}")
    print(f"  SL:        {sl:.2f}  (distance: {entry - sl:.2f})")
    print(f"  TP:        {tp:.2f}  (distance: {tp - entry:.2f})")
    print()
    print(f"Current price:")
    print(f"  Bid: {current_bid:.2f}  Ask: {current_ask:.2f}")
    print()

    unrealized = current_bid - entry
    unrealized_pct = (unrealized / entry) * 100

    print(f"If we had taken the trade:")
    print(f"  Unrealized P&L: {unrealized:+.2f} ({unrealized_pct:+.3f}%)")
    print(f"  On 0.01 lots: ~${unrealized * 0.01 * 100:+.2f}")
    print()

    if current_bid >= tp:
        profit = tp - entry
        print(f"  >> TP HIT! Closed at {tp:.2f}")
        print(f"  >> Profit: +{profit:.2f} (~${profit * 0.01 * 100:.2f})")
    elif current_bid <= sl:
        loss = sl - entry
        print(f"  >> STOPPED OUT at {sl:.2f}")
        print(f"  >> Loss: {loss:.2f} (~${loss * 0.01 * 100:.2f})")
    else:
        print(f"  >> STILL OPEN")
        print(f"  >> Distance to TP: {tp - current_bid:.2f}")
        print(f"  >> Distance to SL: {current_bid - sl:.2f}")

    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M5, 0, 50)
    if rates is not None:
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        recent = df[df["time"] >= "2026-03-12 12:40:00+00:00"]
        if len(recent) > 0:
            high_since = recent["high"].max()
            low_since = recent["low"].min()
            print()
            print(f"Price range since signal:")
            print(f"  Highest: {high_since:.2f}  (TP was {tp:.2f})")
            print(f"  Lowest:  {low_since:.2f}  (SL was {sl:.2f})")
            if high_since >= tp:
                print(f"  >> Price DID reach TP level!")
            if low_since <= sl:
                print(f"  >> Price DID reach SL level!")
else:
    print("Could not get tick data. Is MT5 running?")

mt5.shutdown()
