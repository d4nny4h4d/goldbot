# GoldBot - Intraday Trend Following (ITF)

Automated XAUUSD trading bot using an Intraday Trend Following strategy on the M15 timeframe via MetaTrader 5.

## Strategy

Trades gold by identifying pullbacks within established trends:

- **Trend Filter**: EMA(44) determines directional bias
- **Entry Trigger**: RSI(14) pullback into the 40-60 neutral zone, then turns back in trend direction
- **Trend Strength**: ADX(14) must exceed 25 to confirm a trending market
- **Volatility Sizing**: ATR(14) dynamically scales SL (1.65x ATR), TP (3.0x ATR), and trailing stop
- **Session Filter**: No entries after 19:00 UTC, hard exit at 20:00 UTC

## Architecture

```
src/
  strategy/
    itf_strategy.py      # Core ITF strategy logic
    engine.py            # Strategy orchestrator
    base_strategy.py     # Signal/trade abstractions
  data/
    market_feed.py       # MT5 M15 candle feed
    regime_detector.py   # Market regime classification
  execution/
    mt5_executor.py      # MT5 order execution
  risk/
    manager.py           # Position sizing (2% equity risk), circuit breakers
  db/
    database.py          # SQLite trade journal
  alerts/
    notifier.py          # Telegram trade notifications
  api/
    fastapi_server.py    # Dashboard API endpoint
  main.py               # Entry point
```

## Tech Stack

- **Python 3.11+**
- **MetaTrader5** - Market data and order execution
- **pandas / numpy** - Data processing and indicator calculation
- **SQLite** - Trade journaling
- **Telegram Bot API** - Real-time trade alerts
- **FastAPI** - Dashboard integration

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your MT5 and Telegram credentials
3. Run: `python src/main.py`

## Risk Management

- 2% equity risk per trade
- ATR-based dynamic stop loss and take profit
- Trailing stop locks in profits
- Circuit breaker on consecutive losses
- Session-based time filtering
