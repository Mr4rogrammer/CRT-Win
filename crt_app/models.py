"""Data models used across the CRT app."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Candle:
    """A single OHLC candle."""
    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class SignalResult:
    """Result of evaluating the CRT strategy for one symbol."""
    symbol: str
    signal: str  # "BUY", "SELL", or "NO TRADE"
    reason: str
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None
    c1: Optional[Candle] = None
    c2: Optional[Candle] = None
    c3_time: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    error: Optional[str] = None
