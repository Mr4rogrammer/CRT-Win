"""CRT (Candle Range Theory) price-action reversal strategy.

Rules (objective, backtestable):
  C1 = reference candle (2 candles ago) -> defines range [C1.low, C1.high]
  C2 = candle immediately after C1 (previous completed candle)
  C3 = current/live candle -> entry candle

  Bullish setup (BUY) - low swept:
    - C2.open  > C1.low             (opened inside the range, not gapped below)
    - C2.low   < C1.low              (low of range swept)
    - C2.high  < 50% midpoint of C1  (stayed compressed below the midpoint -
      hasn't already rallied back, preserving reward up to the opposite side)
    - C2.close < 50% midpoint of C1
    -> Entry: current market price
    -> Stop-loss: just below C2.low (the sweep wick) - buffer
    -> Take-profit: C1.high (opposite side of the range)

  Bearish setup (SELL) - high swept (mirror of the above):
    - C2.open  < C1.high            (opened inside the range, not gapped above)
    - C2.high  > C1.high             (high of range swept)
    - C2.low   > 50% midpoint of C1  (stayed compressed above the midpoint)
    - C2.close > 50% midpoint of C1
    -> Entry: current market price
    -> Stop-loss: just above C2.high (the sweep wick) + buffer
    -> Take-profit: C1.low (opposite side of the range)

  No trade:
    - No sweep of either side, or
    - C2 gapped outside the range at open, or
    - Sweep happened but C2 crossed back past the 50% midpoint (too much of the
      move already played out - poor risk:reward, setup invalidated)
"""
from datetime import datetime
from typing import Optional

from .models import Candle, SignalResult

DEFAULT_BUFFER_PCT = 0.05  # 5% of C1's range, used as SL buffer beyond the sweep wick


def evaluate_crt(
    symbol: str,
    c1: Candle,
    c2: Candle,
    current_price: float,
    buffer: Optional[float] = None,
) -> SignalResult:
    """Evaluate the CRT setup given reference candle c1, sweep candle c2,
    and the current live market price (used as the C3 entry reference)."""
    now = datetime.now()
    rng = c1.high - c1.low

    if rng <= 0:
        return SignalResult(
            symbol=symbol,
            signal="NO TRADE",
            reason="Reference candle (C1) has zero/invalid range.",
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    buf = buffer if buffer is not None else rng * DEFAULT_BUFFER_PCT
    midpoint = (c1.high + c1.low) / 2.0

    swept_low = c2.low < c1.low
    swept_high = c2.high > c1.high

    if swept_low and swept_high:
        return SignalResult(
            symbol=symbol,
            signal="NO TRADE",
            reason="Both sides of C1's range were swept by C2 - ambiguous, no valid CRT setup.",
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    if swept_low:
        if c2.open > c1.low and c2.high < midpoint and c2.close < midpoint:
            entry = current_price
            sl = c2.low - buf
            tp = c1.high
            risk = entry - sl
            reward = tp - entry
            rr = (reward / risk) if risk > 0 else None
            return SignalResult(
                symbol=symbol,
                signal="BUY",
                reason=(
                    f"C1 low {c1.low:.5f} swept by C2 (low {c2.low:.5f}), C2 opened inside the "
                    f"range at {c2.open:.5f} and stayed compressed below the 50% midpoint "
                    f"({midpoint:.5f}), closing at {c2.close:.5f}. Bullish CRT setup targeting "
                    f"the opposite side ({c1.high:.5f})."
                ),
                entry=entry,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=rr,
                c1=c1,
                c2=c2,
                c3_time=now,
                evaluated_at=now,
            )
        return SignalResult(
            symbol=symbol,
            signal="NO TRADE",
            reason=(
                f"C1 low was swept by C2, but C2 did not stay compressed below the 50% "
                f"midpoint ({midpoint:.5f}) with an inside open - setup invalidated."
            ),
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    if swept_high:
        if c2.open < c1.high and c2.low > midpoint and c2.close > midpoint:
            entry = current_price
            sl = c2.high + buf
            tp = c1.low
            risk = sl - entry
            reward = entry - tp
            rr = (reward / risk) if risk > 0 else None
            return SignalResult(
                symbol=symbol,
                signal="SELL",
                reason=(
                    f"C1 high {c1.high:.5f} swept by C2 (high {c2.high:.5f}), C2 opened inside "
                    f"the range at {c2.open:.5f} and stayed compressed above the 50% midpoint "
                    f"({midpoint:.5f}), closing at {c2.close:.5f}. Bearish CRT setup targeting "
                    f"the opposite side ({c1.low:.5f})."
                ),
                entry=entry,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=rr,
                c1=c1,
                c2=c2,
                c3_time=now,
                evaluated_at=now,
            )
        return SignalResult(
            symbol=symbol,
            signal="NO TRADE",
            reason=(
                f"C1 high was swept by C2, but C2 did not stay compressed above the 50% "
                f"midpoint ({midpoint:.5f}) with an inside open - setup invalidated."
            ),
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    return SignalResult(
        symbol=symbol,
        signal="NO TRADE",
        reason="C2 did not sweep either side of C1's range - no CRT setup present.",
        c1=c1,
        c2=c2,
        c3_time=now,
        evaluated_at=now,
    )
