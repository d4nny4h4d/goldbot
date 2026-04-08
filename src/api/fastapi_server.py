"""FastAPI REST server — provides data endpoints for the Streamlit dashboard."""

import logging
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.database import Database

logger = logging.getLogger(__name__)

app = FastAPI(title="GoldBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection (read-only for the API)
db = Database()


@app.get("/api/status")
def get_status():
    """System health check."""
    return {"status": "running", "version": "1.0.0"}


@app.get("/api/trades/open")
def get_open_trades():
    """Get currently open trades from the database."""
    return db.get_open_trades()


@app.get("/api/trades/closed")
def get_closed_trades(limit: int = 50):
    """Get recent closed trades."""
    return db.get_closed_trades(limit)


@app.get("/api/trades/today")
def get_today_trades():
    """Get all trades from today."""
    return db.get_today_trades()


@app.get("/api/performance")
def get_performance():
    """Get overall performance statistics."""
    return db.get_performance_stats()


@app.get("/api/daily-summaries")
def get_daily_summaries(days: int = 30):
    """Get daily P&L summaries."""
    return db.get_daily_summaries(days)


@app.get("/api/equity-curve")
def get_equity_curve(limit: int = 1000):
    """Get equity snapshots for charting."""
    return db.get_equity_curve(limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
