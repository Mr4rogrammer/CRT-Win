"""Unit tests for the CRT strategy logic (no MT5 connection required)."""
import unittest
from datetime import datetime, timedelta

from crt_app.models import Candle
from crt_app.strategy import evaluate_crt


def make_candle(days_ago, o, h, l, c):
    return Candle(
        time=datetime.now() - timedelta(days=days_ago),
        open=o, high=h, low=l, close=c,
    )


class TestCRTStrategy(unittest.TestCase):
    def test_bullish_low_sweep_and_reject(self):
        # C1: high=100 low=90 -> midpoint = 95
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        # C2: opens at 93 (inside range), wicks to 88 (sweeps low), stays
        # compressed below the 95 midpoint, closes at 92.
        c2 = make_candle(1, o=93, h=94, l=88, c=92)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=92)
        self.assertEqual(result.signal, "BUY")
        self.assertAlmostEqual(result.take_profit, 100)
        self.assertLess(result.stop_loss, c2.low)

    def test_bearish_high_sweep_and_reject(self):
        # C1: high=100 low=90 -> midpoint = 95
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        # C2: opens at 97 (inside range), wicks to 102 (sweeps high), stays
        # compressed above the 95 midpoint, closes at 98.
        c2 = make_candle(1, o=97, h=102, l=96, c=98)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=98)
        self.assertEqual(result.signal, "SELL")
        self.assertAlmostEqual(result.take_profit, 90)
        self.assertGreater(result.stop_loss, c2.high)

    def test_no_sweep_no_trade(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=97, h=99, l=93, c=96)  # stays fully inside range
        result = evaluate_crt("EURUSD", c1, c2, entry_price=96)
        self.assertEqual(result.signal, "NO TRADE")

    def test_both_sides_swept_is_ambiguous(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=95, h=102, l=88, c=95)  # sweeps both high and low
        result = evaluate_crt("EURUSD", c1, c2, entry_price=95)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIn("ambiguous", result.reason.lower())

    def test_low_sweep_but_close_crosses_past_midpoint_is_no_trade(self):
        # Sweeps the low, but rallies back past the 95 midpoint already -
        # too much of the move has played out, poor risk:reward.
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        c2 = make_candle(1, o=93, h=99, l=88, c=97)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=97)
        self.assertEqual(result.signal, "NO TRADE")

    def test_high_sweep_but_close_crosses_past_midpoint_is_no_trade(self):
        # Sweeps the high, but falls back past the 95 midpoint already -
        # too much of the move has played out, poor risk:reward.
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=97, h=101, l=91, c=93)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=93)
        self.assertEqual(result.signal, "NO TRADE")

    def test_low_sweep_but_gapped_below_open_is_no_trade(self):
        # C2 opens at/below C1's low instead of inside the range.
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        c2 = make_candle(1, o=89, h=91, l=87, c=90)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=90)
        self.assertEqual(result.signal, "NO TRADE")

    def test_high_sweep_but_gapped_above_open_is_no_trade(self):
        # C2 opens at/above C1's high instead of inside the range.
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=101, h=103, l=99, c=100)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=100)
        self.assertEqual(result.signal, "NO TRADE")

    def test_zero_range_reference_candle(self):
        c1 = make_candle(2, o=100, h=100, l=100, c=100)
        c2 = make_candle(1, o=100, h=101, l=99, c=100)
        result = evaluate_crt("EURUSD", c1, c2, entry_price=100)
        self.assertEqual(result.signal, "NO TRADE")

    def test_custom_threshold_stricter_rejects_setup_that_passes_at_50pct(self):
        # C1: high=100 low=90. At the default 50% (level=95) this C2 qualifies
        # as BUY (close=94 < 95). With a stricter 20% threshold (level=92),
        # close=94 now crosses past it -> NO TRADE.
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        c2 = make_candle(1, o=93, h=94, l=88, c=94)
        default_result = evaluate_crt("EURUSD", c1, c2, entry_price=94)
        self.assertEqual(default_result.signal, "BUY")

        strict_result = evaluate_crt("EURUSD", c1, c2, entry_price=94, threshold_pct=0.2)
        self.assertEqual(strict_result.signal, "NO TRADE")

    def test_custom_threshold_more_lenient_allows_setup_that_fails_at_50pct(self):
        # C1: high=100 low=90. At default 50% (level=95), C2's low (93.5) and
        # close (94) fall short -> NO TRADE. With a more lenient 70% threshold
        # (level=93), the same C2 now qualifies as SELL.
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=97, h=101, l=93.5, c=94)
        default_result = evaluate_crt("EURUSD", c1, c2, entry_price=94)
        self.assertEqual(default_result.signal, "NO TRADE")

        lenient_result = evaluate_crt("EURUSD", c1, c2, entry_price=94, threshold_pct=0.7)
        self.assertEqual(lenient_result.signal, "SELL")

    def test_sell_setup_invalidated_when_live_price_already_past_stop_loss(self):
        # Valid SELL setup at C2's close, but by the time we check, the live
        # price has already rallied past the stop-loss level -> NO TRADE,
        # never a SELL with a negative/nonsensical risk:reward.
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=97, h=101, l=96, c=98)  # sl would be 101.5
        result = evaluate_crt("EURUSD", c1, c2, entry_price=103)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIsNone(result.risk_reward)

    def test_buy_setup_invalidated_when_live_price_already_past_stop_loss(self):
        # Valid BUY setup at C2's close, but by the time we check, the live
        # price has already fallen past the stop-loss level -> NO TRADE.
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        c2 = make_candle(1, o=93, h=94, l=88, c=92)  # sl would be 87.5
        result = evaluate_crt("EURUSD", c1, c2, entry_price=86)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIsNone(result.risk_reward)


if __name__ == "__main__":
    unittest.main()
