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
    def test_bearish_high_sweep_and_reject(self):
        # Reference candle: high=100 low=90 -> midpoint = 95
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        # Sweep: 100 -> 101 -> back to 93 (closes below the 95 midpoint)
        c2 = make_candle(1, o=99, h=101, l=92, c=93)
        result = evaluate_crt("EURUSD", c1, c2, current_price=93)
        self.assertEqual(result.signal, "SELL")
        self.assertAlmostEqual(result.take_profit, 90)
        self.assertGreater(result.stop_loss, c2.high)

    def test_bullish_low_sweep_and_reject(self):
        # Reference candle: high=100 low=90 -> midpoint = 95
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        # Sweep: 90 -> 89 -> back to 97 (closes above the 95 midpoint)
        c2 = make_candle(1, o=91, h=98, l=89, c=97)
        result = evaluate_crt("EURUSD", c1, c2, current_price=97)
        self.assertEqual(result.signal, "BUY")
        self.assertAlmostEqual(result.take_profit, 100)
        self.assertLess(result.stop_loss, c2.low)

    def test_bearish_sweep_but_close_stays_above_midpoint_is_no_trade(self):
        # Closes back inside the range, but only to 99 - above the 95 midpoint.
        c1 = make_candle(2, o=95, h=100, l=90, c=93)
        c2 = make_candle(1, o=99, h=101, l=98, c=99)
        result = evaluate_crt("EURUSD", c1, c2, current_price=99)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIn("midpoint", result.reason.lower())

    def test_bullish_sweep_but_close_stays_below_midpoint_is_no_trade(self):
        # Closes back inside the range, but only to 92 - below the 95 midpoint.
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=91, h=93, l=89, c=92)
        result = evaluate_crt("EURUSD", c1, c2, current_price=92)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIn("midpoint", result.reason.lower())

    def test_no_sweep_no_trade(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=97, h=99, l=93, c=96)  # stays fully inside range
        result = evaluate_crt("EURUSD", c1, c2, current_price=96)
        self.assertEqual(result.signal, "NO TRADE")

    def test_both_sides_swept_is_ambiguous(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=95, h=102, l=88, c=95)  # sweeps both high and low
        result = evaluate_crt("EURUSD", c1, c2, current_price=95)
        self.assertEqual(result.signal, "NO TRADE")
        self.assertIn("ambiguous", result.reason.lower())

    def test_sweep_without_close_back_inside_invalidates_bearish(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=99, h=103, l=98, c=101)  # closes above range high -> no reject
        result = evaluate_crt("EURUSD", c1, c2, current_price=101)
        self.assertEqual(result.signal, "NO TRADE")

    def test_sweep_without_close_back_inside_invalidates_bullish(self):
        c1 = make_candle(2, o=95, h=100, l=90, c=97)
        c2 = make_candle(1, o=91, h=92, l=87, c=88)  # closes below range low -> no reject
        result = evaluate_crt("EURUSD", c1, c2, current_price=88)
        self.assertEqual(result.signal, "NO TRADE")

    def test_zero_range_reference_candle(self):
        c1 = make_candle(2, o=100, h=100, l=100, c=100)
        c2 = make_candle(1, o=100, h=101, l=99, c=100)
        result = evaluate_crt("EURUSD", c1, c2, current_price=100)
        self.assertEqual(result.signal, "NO TRADE")


if __name__ == "__main__":
    unittest.main()
