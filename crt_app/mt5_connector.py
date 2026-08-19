"""Wrapper around the MetaTrader5 Python package.

NOTE: The `MetaTrader5` package only works on Windows, and only when the
MetaTrader 5 terminal is installed and running locally on the same machine.
This module fails gracefully (raises a clear RuntimeError) when the package
or terminal is unavailable, so the rest of the app (UI, strategy, storage)
can still be developed/tested on other platforms.
"""
from datetime import datetime
from typing import List

from .models import Candle

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class MT5Connector:
    """Manages the connection to a locally running MT5 terminal and fetches data."""

    def __init__(self):
        self.connected = False

    def connect(self) -> None:
        if not MT5_AVAILABLE:
            raise RuntimeError(
                "The 'MetaTrader5' package is only available on Windows. "
                "Install it with 'pip install MetaTrader5' and make sure the "
                "MetaTrader 5 terminal is installed and running on this machine."
            )
        if not mt5.initialize():
            code, desc = mt5.last_error()
            raise RuntimeError(
                f"MT5 initialize() failed (error {code}: {desc}). "
                "Make sure the MetaTrader 5 terminal is running and logged in."
            )
        self.connected = True

    def shutdown(self) -> None:
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False

    def terminal_info(self):
        if not MT5_AVAILABLE or not self.connected:
            return None
        return mt5.terminal_info()

    def get_daily_candles(self, symbol: str, count: int = 3) -> List[Candle]:
        """Returns `count` daily candles, most recent first.
        Index 0 = current/live (forming) candle -> C3
        Index 1 = last completed candle -> C2
        Index 2 = candle before that -> C1 (reference)
        """
        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not available on this platform.")
        if not self.connected:
            raise RuntimeError("Not connected to MT5. Call connect() first.")

        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Symbol '{symbol}' could not be selected in Market Watch.")

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, count)
        if rates is None or len(rates) < count:
            code, desc = mt5.last_error()
            raise RuntimeError(
                f"Could not fetch {count} daily candles for '{symbol}' "
                f"(error {code}: {desc})."
            )

        candles = [
            Candle(
                time=datetime.fromtimestamp(int(r["time"])),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
            )
            for r in rates
        ]
        # copy_rates_from_pos returns oldest -> newest; reverse to newest-first.
        candles.reverse()
        return candles

    def get_current_price(self, symbol: str) -> float:
        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not available on this platform.")
        if not self.connected:
            raise RuntimeError("Not connected to MT5. Call connect() first.")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Could not fetch current tick for '{symbol}'.")
        return (tick.bid + tick.ask) / 2.0

    def get_all_symbols(self) -> List[str]:
        """Returns every symbol available in the connected MT5 terminal's
        Market Watch/broker symbol list (e.g. all forex pairs, indices,
        metals, etc.), sorted alphabetically."""
        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not available on this platform.")
        if not self.connected:
            raise RuntimeError("Not connected to MT5. Call connect() first.")

        symbols = mt5.symbols_get()
        if symbols is None:
            code, desc = mt5.last_error()
            raise RuntimeError(f"Could not fetch symbol list (error {code}: {desc}).")
        return sorted(s.name for s in symbols)
