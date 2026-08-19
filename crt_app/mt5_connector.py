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


# Human-friendly timeframe labels -> MT5 timeframe constants. Built lazily
# (only when MT5_AVAILABLE) since `mt5.TIMEFRAME_*` constants don't exist
# when the package couldn't be imported (e.g. on macOS/Linux dev machines).
if MT5_AVAILABLE:
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
else:
    # Placeholder keys so the UI (which needs the list of supported labels)
    # can still be built and tested on non-Windows machines.
    TIMEFRAME_MAP = {
        "M1": None, "M5": None, "M15": None, "M30": None,
        "H1": None, "H4": None, "D1": None, "W1": None, "MN1": None,
    }


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

    def get_daily_candles(self, symbol: str, count: int = 3, timeframe: str = "D1") -> List[Candle]:
        """Returns `count` candles on the given `timeframe`, most recent first.
        Index 0 = current/live (forming) candle -> C3
        Index 1 = last completed candle -> C2
        Index 2 = candle before that -> C1 (reference)

        `timeframe` is one of the keys in TIMEFRAME_MAP (e.g. "M15", "H1",
        "H4", "D1", "W1"). Despite the method name, this works for any
        supported timeframe, not just daily.
        """
        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not available on this platform.")
        if not self.connected:
            raise RuntimeError("Not connected to MT5. Call connect() first.")

        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Symbol '{symbol}' could not be selected in Market Watch.")

        tf_const = TIMEFRAME_MAP.get(timeframe)
        if tf_const is None:
            raise RuntimeError(
                f"Unsupported timeframe '{timeframe}'. Supported: {', '.join(TIMEFRAME_MAP)}."
            )

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
        if rates is None or len(rates) < count:
            code, desc = mt5.last_error()
            raise RuntimeError(
                f"Could not fetch {count} {timeframe} candles for '{symbol}' "
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
