"""Abstract base class for all trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SignalDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    NONE = "none"


@dataclass
class TradeSignal:
    """A signal emitted by a strategy."""
    direction: SignalDirection
    entry_price: float
    sl_price: float
    tp_price: float
    sl_distance: float          # price distance from entry to SL
    strategy_name: str
    confidence: float = 1.0     # 0-1 scale, for future use
    reason: str = ""


class BaseStrategy(ABC):
    """All strategies must implement this interface."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", False)

    @abstractmethod
    def generate_signal(self, candles: pd.DataFrame, tick: dict) -> TradeSignal | None:
        """Analyze candles and current tick, return a signal or None.

        Args:
            candles: DataFrame with OHLCV data (time-indexed, columns: open, high, low, close, tick_volume)
            tick: Dict with keys: bid, ask, spread, time

        Returns:
            TradeSignal if entry conditions met, None otherwise
        """
        ...

    @abstractmethod
    def should_close(self, position: dict, candles: pd.DataFrame, tick: dict) -> bool:
        """Check if an open position from this strategy should be closed.

        Used for trailing stops, time exits, etc. that go beyond fixed SL/TP.

        Args:
            position: Dict with position details (ticket, direction, entry_price, etc.)
            candles: Current candle data
            tick: Current tick

        Returns:
            True if position should be closed
        """
        ...

    def is_active_session(self, utc_hour: int) -> bool:
        """Check if the current UTC hour is within this strategy's active session."""
        sessions = self.config.get("sessions", ["all"])
        if "all" in sessions:
            return True
        # Subclasses can override for specific session windows
        return True
