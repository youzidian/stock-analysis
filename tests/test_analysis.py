import unittest

from stock_analyzer.analysis import build_summary, enrich_prices, lrc_channel, lrc_snapshot, rsi, sma


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


if __name__ == "__main__":
    unittest.main()
