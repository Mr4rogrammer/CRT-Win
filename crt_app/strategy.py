"""CRT (Candle Range Theory) price-action reversal strategy.

Rules (objective, backtestable):
  C1 = reference candle (2 candles ago) -> defines range [C1.low, C1.high]
  C2 = candle immediately after C1 (previous completed candle)
  C3 = current/live candle -> entry candle

  Bearish setup (SELL):
    - C2.high > C1.high            (high of range swept)
    - C2.low  >= C1.low             (low NOT also swept -> unambiguous)
    - C2.close < 50% level of C1's range (midpoint)  (strong reject back through
      more than half the range, not just a marginal close back inside)
    -> Entry: current market price
    -> Stop-loss: just above C2.high (the sweep wick) + buffer
    -> Take-profit: C1.low (opposite side of the range)

  Bullish setup (BUY):
    - C2.low  < C1.low              (low of range swept)
    - C2.high <= C1.high            (high NOT also swept -> unambiguous)
    - C2.close > 50% level of C1's range (midpoint)  (strong reject back through
      more than half the range, not just a marginal close back inside)
    -> Entry: current market price
    -> Stop-loss: just below C2.low (the sweep wick) - buffer
    -> Take-profit: C1.high (opposite side of the range)

  No trade:
    - No sweep of either side, or
    - Both sides swept in the same candle (ambiguous), or
    - Swept but candle did not close back past the 50% midpoint of C1's range (invalidated)
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
    """Evaluate the CRT setup given reference candle c1, sweep/reject candle c2,
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

    swept_high = c2.high > c1.high
    swept_low = c2.low < c1.low

    if swept_high and swept_low:
        return SignalResult(
            symbol=symbol,
            signal="NO TRADE",
            reason="Both sides of C1's range were swept by C2 - ambiguous, no valid CRT setup.",
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    if swept_high:
        if c2.close < midpoint:
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
                    f"C1 high {c1.high:.5f} swept by C2 (high {c2.high:.5f}) and C2 closed "
                    f"back below the 50% midpoint ({midpoint:.5f}) at {c2.close:.5f}. "
                    f"Bearish CRT setup targeting the opposite side ({c1.low:.5f})."
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
                f"C1 high was swept but C2 closed at {c2.close:.5f}, which did not cross back "
                f"below the 50% midpoint ({midpoint:.5f}) of C1's range - setup invalidated."
            ),
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    if swept_low:
        if c2.close > midpoint:
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
                    f"C1 low {c1.low:.5f} swept by C2 (low {c2.low:.5f}) and C2 closed "
                    f"back above the 50% midpoint ({midpoint:.5f}) at {c2.close:.5f}. "
                    f"Bullish CRT setup targeting the opposite side ({c1.high:.5f})."
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
                f"C1 low was swept but C2 closed at {c2.close:.5f}, which did not cross back "
                f"above the 50% midpoint ({midpoint:.5f}) of C1's range - setup invalidated."
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
