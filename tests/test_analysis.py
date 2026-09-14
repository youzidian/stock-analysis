import unittest
from datetime import date, timedelta

from stock_analyzer.analysis import (
    build_ma_slope_summary,
    build_summary,
    enrich_prices,
    lrc_channel,
    lrc_snapshot,
    rolling_lrc_z_scores,
    rsi,
    sma,
)


class AnalysisTests(unittest.TestCase):
    def test_sma_leaves_initial_values_empty(self):
        self.assertEqual(sma([1, 2, 3, 4], 3), [None, None, 2, 3])

    def test_rsi_outputs_high_value_for_steady_gains(self):
        values = [float(value) for value in range(1, 25)]
        result = rsi(values)
        self.assertEqual(result[-1], 100.0)

    def test_enrich_prices_adds_expected_fields(self):
        rows = [
            {
                "date": f"2026-01-{idx + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1000 + idx,
            }
            for idx in range(60)
        ]
        enriched = enrich_prices(rows)
        self.assertIsNotNone(enriched[-1]["sma20"])
        self.assertIsNotNone(enriched[-1]["sma50"])
        self.assertGreater(enriched[-1]["change_pct"], 0)

    def test_build_summary_scores_trending_market(self):
        rows = [
            {
                "date": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1000,
            }
            for idx in range(260)
        ]
        summary = build_summary("test", rows)
        self.assertEqual(summary["symbol"], "TEST")
        self.assertGreaterEqual(summary["score"]["value"], 60)
        self.assertGreater(len(summary["signals"]), 0)

    def test_build_ma_slope_summary_uses_percent_per_day_formula(self):
        rows = [
            {
                "date": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1000 + idx,
            }
            for idx in range(80)
        ]
        summary = build_ma_slope_summary(
            "test",
            rows,
            periods=[20, 50],
            slope_window=5,
            display_rows=40,
        )

        self.assertEqual(summary["symbol"], "TEST")
        self.assertEqual(summary["periods"], [20, 50])
        self.assertEqual(len(summary["rows"]), 40)
        latest = summary["rows"][-1]
        current_ma20 = latest["mas"]["20"]
        previous_ma20 = summary["rows"][-6]["mas"]["20"]
        expected = (current_ma20 / previous_ma20 - 1) * 100 / 5
        self.assertAlmostEqual(latest["slopes"]["20"], expected)
        self.assertLess(summary["metrics"][0]["priceVsMaPct"], 0)
        self.assertIn("minDate", summary["statistics"][0])

    def test_build_ma_slope_summary_uses_calendar_start_date(self):
        start = date(2024, 1, 1)
        rows = [
            {
                "date": str(start + timedelta(days=idx)),
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1000,
            }
            for idx in range(90)
        ]
        summary = build_ma_slope_summary(
            "test",
            rows,
            periods=[20],
            slope_window=5,
            display_start_date=date(2024, 3, 1),
        )
        self.assertEqual(summary["rows"][0]["date"], "2024-03-01")

    def test_lrc_snapshot_uses_newest_first_regression_channel(self):
        rows = [
            {
                "date": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 10 + idx,
                "high": 10 + idx,
                "low": 10 + idx,
                "close": 12 + idx if idx == 19 else 10 + idx,
                "volume": 1000,
            }
            for idx in range(20)
        ]
        snapshot = lrc_snapshot(rows, window=10)
        self.assertEqual(snapshot.window, 10)
        self.assertGreater(snapshot.z_score, 0)
        self.assertAlmostEqual(
            snapshot.z_score, snapshot.residual / snapshot.stddev, places=8
        )

    def test_lrc_snapshot_prefers_adjusted_close(self):
        rows = [
            {
                "date": f"2026-01-{idx + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx + (4 if idx == 19 else 0),
                "adj_close": (
                    (100 + idx) * 0.94
                    if idx < 10
                    else 100 + idx + (2 if idx == 19 else 0)
                ),
                "volume": 1000,
            }
            for idx in range(20)
        ]
        adjusted_snapshot = lrc_snapshot(rows, window=20)
        raw_snapshot = lrc_snapshot(
            [{key: value for key, value in row.items() if key != "adj_close"} for row in rows],
            window=20,
        )
        self.assertAlmostEqual(adjusted_snapshot.latest_close, rows[-1]["adj_close"])
        self.assertNotAlmostEqual(adjusted_snapshot.z_score, raw_snapshot.z_score)

    def test_lrc_channel_returns_window_rows_with_bands(self):
        rows = [
            {
                "date": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 10 + idx,
                "high": 10 + idx,
                "low": 10 + idx,
                "close": 12 + idx if idx == 19 else 10 + idx,
                "volume": 1000,
            }
            for idx in range(20)
        ]
        channel = lrc_channel(rows, window=10)
        self.assertEqual(len(channel), 10)
        self.assertIn("upper2", channel[-1])
        self.assertEqual(channel[-1]["date"], rows[-1]["date"])

    def test_rolling_lrc_z_scores_start_after_full_window(self):
        rows = [
            {
                "date": f"2026-{(idx // 28) + 1:02d}-{(idx % 28) + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx + (3 if idx % 17 == 0 else 0),
                "volume": 1000,
            }
            for idx in range(220)
        ]
        values = rolling_lrc_z_scores(rows, window=200)
        self.assertEqual(len(values), len(rows))
        self.assertTrue(all(value is None for value in values[:199]))
        self.assertIsNotNone(values[199])

        summary = build_summary("test", rows)
        self.assertIn("lrc_zscore", summary["rows"][-1])


if __name__ == "__main__":
    unittest.main()
