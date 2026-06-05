import tempfile
import unittest
from pathlib import Path

from stock_analyzer.cache_builder import load_symbol_records, load_symbols
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


if __name__ == "__main__":
    unittest.main()
