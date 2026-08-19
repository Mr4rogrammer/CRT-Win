"""Ties together the MT5 connector and the CRT strategy for one or many symbols."""
from datetime import datetime
from typing import List

from .models import SignalResult
from .mt5_connector import MT5Connector
from .strategy import evaluate_crt


def analyze_symbol(connector: MT5Connector, symbol: str, threshold_pct: float = 0.5) -> SignalResult:
    """Fetch daily candles for `symbol` and evaluate the CRT strategy.
    Never raises - returns a SignalResult with signal="ERROR" on failure.
    """
    try:
        candles = connector.get_daily_candles(symbol, count=3)
        c3_forming, c2, c1 = candles[0], candles[1], candles[2]
        current_price = connector.get_current_price(symbol)
        result = evaluate_crt(symbol, c1, c2, current_price, threshold_pct=threshold_pct)
        result.c3_time = c3_forming.time
        return result
    except Exception as exc:  # noqa: BLE001 - surface any MT5/network error to the UI
        return SignalResult(
            symbol=symbol,
            signal="ERROR",
            reason=str(exc),
            error=str(exc),
            evaluated_at=datetime.now(),
        )


def analyze_symbols(connector: MT5Connector, symbols: List[str], threshold_pct: float = 0.5) -> List[SignalResult]:
    return [analyze_symbol(connector, s, threshold_pct=threshold_pct) for s in symbols]
