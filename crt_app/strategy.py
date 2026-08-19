"""CRT (Candle Range Theory) price-action reversal strategy.

Rules (objective, backtestable):
  C1 = reference candle (2 candles ago) -> defines range [C1.low, C1.high]
  C2 = candle immediately after C1 (previous completed candle)
  C3 = current/live candle -> entry candle

  A configurable `threshold_pct` (default 0.5 = 50%) defines how far back
  into C1's range, measured from the swept side, C2 is allowed to close.
  Lower values (e.g. 0.3) make the rule stricter (C2 must stay very close to
  the swept extreme). Higher values (e.g. 0.7) make it more lenient.

  Bullish setup (BUY) - low swept:
    - C2.open  > C1.low             (opened inside the range, not gapped below)
    - C2.low   < C1.low              (low of range swept)
    - level = C1.low + threshold_pct * (C1.high - C1.low)
    - C2.high  < level               (stayed compressed below the threshold level -
      hasn't already rallied back, preserving reward up to the opposite side)
    - C2.close < level
    -> Entry: C3 (today's daily candle) open price
    -> Stop-loss: just below C2.low (the sweep wick) - buffer
    -> Take-profit: C1.high (opposite side of the range)

  Bearish setup (SELL) - high swept (mirror of the above):
    - C2.open  < C1.high            (opened inside the range, not gapped above)
    - C2.high  > C1.high             (high of range swept)
    - level = C1.high - threshold_pct * (C1.high - C1.low)
    - C2.low   > level               (stayed compressed above the threshold level)
    - C2.close > level
    -> Entry: C3 (today's daily candle) open price
    -> Stop-loss: just above C2.high (the sweep wick) + buffer
    -> Take-profit: C1.low (opposite side of the range)

  No trade:
    - No sweep of either side, or
    - C2 gapped outside the range at open, or
    - Sweep happened but C2 crossed back past the threshold level (too much of
      the move already played out - poor risk:reward, setup invalidated)
"""
from datetime import datetime
from typing import Optional

from .models import Candle, SignalResult

DEFAULT_BUFFER_PCT = 0.05  # 5% of C1's range, used as SL buffer beyond the sweep wick
DEFAULT_THRESHOLD_PCT = 0.5  # 50% (midpoint) by default, user-configurable


def evaluate_crt(
    symbol: str,
    c1: Candle,
    c2: Candle,
    entry_price: float,
    buffer: Optional[float] = None,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
) -> SignalResult:
    """Evaluate the CRT setup given reference candle c1, sweep candle c2,
    the C3 (today's) daily candle open price used as the entry reference, and a
    configurable threshold_pct (0 < threshold_pct < 1) - the fraction of C1's
    range, measured from the swept side, that C2 must stay within."""
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

    if not 0 < threshold_pct < 1:
        threshold_pct = DEFAULT_THRESHOLD_PCT

    buf = buffer if buffer is not None else rng * DEFAULT_BUFFER_PCT
    threshold_label = f"{threshold_pct * 100:.0f}%"

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
        level = c1.low + threshold_pct * rng
        if c2.open > c1.low and c2.high < level and c2.close < level:
            entry = entry_price
            sl = c2.low - buf
            tp = c1.high
            risk = entry - sl
            reward = tp - entry
            # Guard against a stale/invalidated setup: if the live price has
            # already moved past the stop-loss or the take-profit since C2
            # closed, this is no longer a valid tradeable entry.
            if risk <= 0 or reward <= 0:
                return SignalResult(
                    symbol=symbol,
                    signal="NO TRADE",
                    reason=(
                        f"Bullish CRT setup found (C1 low swept by C2), but the current "
                        f"price {entry:.5f} has already moved past the stop-loss "
                        f"({sl:.5f}) or take-profit ({tp:.5f}) since C2 closed - "
                        f"setup no longer tradeable."
                    ),
                    entry=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    c1=c1,
                    c2=c2,
                    c3_time=now,
                    evaluated_at=now,
                )
            rr = reward / risk
            return SignalResult(
                symbol=symbol,
                signal="BUY",
                reason=(
                    f"C1 low {c1.low:.5f} swept by C2 (low {c2.low:.5f}), C2 opened inside the "
                    f"range at {c2.open:.5f} and stayed compressed below the {threshold_label} "
                    f"level ({level:.5f}), closing at {c2.close:.5f}. Bullish CRT setup "
                    f"targeting the opposite side ({c1.high:.5f})."
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
                f"C1 low was swept by C2, but C2 did not stay compressed below the "
                f"{threshold_label} level ({level:.5f}) with an inside open - setup invalidated."
            ),
            c1=c1,
            c2=c2,
            c3_time=now,
            evaluated_at=now,
        )

    if swept_high:
        level = c1.high - threshold_pct * rng
        if c2.open < c1.high and c2.low > level and c2.close > level:
            entry = entry_price
            sl = c2.high + buf
            tp = c1.low
            risk = sl - entry
            reward = entry - tp
            # Guard against a stale/invalidated setup: if the live price has
            # already moved past the stop-loss or the take-profit since C2
            # closed, this is no longer a valid tradeable entry.
            if risk <= 0 or reward <= 0:
                return SignalResult(
                    symbol=symbol,
                    signal="NO TRADE",
                    reason=(
                        f"Bearish CRT setup found (C1 high swept by C2), but the current "
                        f"price {entry:.5f} has already moved past the stop-loss "
                        f"({sl:.5f}) or take-profit ({tp:.5f}) since C2 closed - "
                        f"setup no longer tradeable."
                    ),
                    entry=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    c1=c1,
                    c2=c2,
                    c3_time=now,
                    evaluated_at=now,
                )
            rr = reward / risk
            return SignalResult(
                symbol=symbol,
                signal="SELL",
                reason=(
                    f"C1 high {c1.high:.5f} swept by C2 (high {c2.high:.5f}), C2 opened inside "
                    f"the range at {c2.open:.5f} and stayed compressed above the "
                    f"{threshold_label} level ({level:.5f}), closing at {c2.close:.5f}. "
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
                f"C1 high was swept by C2, but C2 did not stay compressed above the "
                f"{threshold_label} level ({level:.5f}) with an inside open - setup invalidated."
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
