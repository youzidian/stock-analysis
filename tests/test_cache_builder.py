import tempfile
import unittest
from pathlib import Path

from stock_analyzer.cache_builder import (
    CacheResult,
    SymbolRecord,
    load_failed_symbols,
    load_symbol_records,
    load_symbols,
    sigma_fields,
    write_failed_symbols,
)
from stock_analyzer.data import BASE_PERIOD
from tools.create_symbols_xlsx import write_xlsx


class CacheBuilderTests(unittest.TestCase):
    def test_load_symbols_ignores_comments_blanks_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "symbols.txt"
            path.write_text(
                "\n# comment\naapl\nMSFT # inline\nAAPL\n\n0700.hk\n",
                encoding="utf-8",
            )

            self.assertEqual(load_symbols(path), ["AAPL", "MSFT", "0700.HK"])

    def test_load_symbols_from_xlsx_uses_enabled_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "symbols.xlsx"
            write_xlsx(
                path,
                {
                    "US": [
                        ["symbol", "name", "enabled", "industry"],
                        ["AAPL", "Apple", "TRUE", "Consumer Electronics"],
                        ["MSFT", "Microsoft", "FALSE", "Software"],
                    ],
                    "HK": [
                        ["symbol", "name", "enabled", "industry"],
                        ["0700.HK", "Tencent", "", "Internet"],
                    ],
                },
            )

            self.assertEqual(load_symbols(path), ["AAPL", "0700.HK"])
            records = load_symbol_records(path)
            self.assertEqual(records[0].industry, "Consumer Electronics")
            self.assertEqual(records[1].industry, "Internet")

    def test_load_symbols_filters_by_sheet_market(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "symbols.xlsx"
            write_xlsx(
                path,
                {
                    "US": [
                        ["symbol", "name", "enabled"],
                        ["AAPL", "Apple", "TRUE"],
                        ["SPY", "S&P 500 ETF", "TRUE"],
                    ],
                    "HK": [
                        ["symbol", "name", "enabled"],
                        ["0700.HK", "Tencent", "TRUE"],
                    ],
                },
            )

            self.assertEqual(load_symbols(path, markets={"HK"}), ["0700.HK"])
            self.assertEqual(load_symbols(path, markets={"US"}), ["AAPL", "SPY"])

    def test_failed_symbol_file_removes_successful_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failed_symbols.json"
            write_failed_symbols(
                [
                    CacheResult(
                        "SAN",
                        BASE_PERIOD,
                        False,
                        error="HTTP 502",
                        action="failed",
                    ),
                    CacheResult("BROS", BASE_PERIOD, True, action="updated"),
                ],
                path,
                previous_symbols={"SAN", "BROS", "OTHER"},
                attempted_symbols={"SAN", "BROS"},
            )

            self.assertEqual(load_failed_symbols(path), {"SAN", "OTHER"})

    def test_sigma_fields_include_ma20_ma50_and_ma200(self):
        rows = [
            {
                "date": f"2026-01-{(idx % 28) + 1:02d}",
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1000,
            }
            for idx in range(220)
        ]
        from stock_analyzer.analysis import enrich_prices

        fields = sigma_fields(
            SymbolRecord("TEST", "US", "Test Inc.", "TRUE", "Software"),
            rows,
            enrich_prices(rows),
            {"marketCap": 1_000_000, "operatingProfit": 250_000},
            0.5,
        )

        self.assertIsNotNone(fields["MA-MA20-日線"])
        self.assertIsNotNone(fields["MA-MA50-日線"])
        self.assertIsNotNone(fields["MA-MA200-日線"])
        self.assertEqual(fields["市值"], 1_000_000)
        self.assertEqual(fields["營業利潤(TTM)"], 250_000)


if __name__ == "__main__":
    unittest.main()
