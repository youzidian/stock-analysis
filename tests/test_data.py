import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from stock_analyzer.data import (
    BASE_PERIOD,
    CACHE_SCHEMA_VERSION,
    PRICE_MODE,
    YahooChartProvider,
)


def price_row(date_value: str, close: float) -> dict[str, object]:
    return {
        "date": date_value,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "adj_close": close,
        "volume": 100,
    }


class FakeProvider(YahooChartProvider):
    def __init__(self, cache_dir: Path, fresh_rows: list[dict[str, object]]) -> None:
        super().__init__(cache_dir, retry_delays=(0, 0, 0))
        self.fresh_rows = fresh_rows
        self.fetch_periods: list[str] = []

    def _fetch(self, symbol: str, period: str) -> dict[str, object]:
        self.fetch_periods.append(period)
        return {"period": period}

    def _parse_chart(
        self, payload: dict[str, object]
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        return self.fresh_rows, {"currency": "USD"}


class CorporateActionProvider(FakeProvider):
    def _fetch(self, symbol: str, period: str) -> dict[str, object]:
        self.fetch_periods.append(period)
        if period == "1mo":
            timestamp = int(
                datetime(2026, 6, 10, tzinfo=timezone.utc).timestamp()
            )
            return {
                "chart": {
                    "result": [
                        {
                            "events": {
                                "dividends": {
                                    str(timestamp): {"date": timestamp, "amount": 0.5}
                                }
                            }
                        }
                    ]
                },
                "period": period,
            }
        return {"period": period}


class DataCacheTests(unittest.TestCase):
    def test_up_to_date_cache_is_skipped_without_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(Path(tmp), [price_row("2026-06-10", 101)])
            provider._write_base_cache("TEST", [price_row("2026-06-10", 100)], {})

            result = provider.update_base_cache("TEST", target_date="2026-06-10")

            self.assertEqual(result.action, "skipped")
            self.assertEqual(provider.fetch_periods, [])

    def test_stale_cache_fetches_incremental_and_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(
                Path(tmp),
                [price_row("2026-06-09", 101), price_row("2026-06-10", 102)],
            )
            provider._write_base_cache("TEST", [price_row("2026-06-09", 100)], {})

            result = provider.update_base_cache("TEST", target_date="2026-06-10")

            self.assertEqual(result.action, "updated")
            self.assertEqual(provider.fetch_periods, ["1mo"])
            self.assertEqual(result.rows[-1]["date"], "2026-06-10")
            self.assertEqual(result.rows[-2]["close"], 101)

    def test_outdated_schema_triggers_full_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            path = cache_dir / "prices" / "TEST.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": CACHE_SCHEMA_VERSION - 1,
                        "priceMode": PRICE_MODE,
                        "rows": [price_row("2026-06-09", 100)],
                        "meta": {},
                    }
                ),
                encoding="utf-8",
            )
            provider = FakeProvider(cache_dir, [price_row("2026-06-10", 102)])

            result = provider.update_base_cache("TEST", target_date="2026-06-10")

            self.assertEqual(result.action, "rebuilt")
            self.assertEqual(provider.fetch_periods, [BASE_PERIOD])

    def test_old_range_cache_triggers_six_year_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            path = cache_dir / "prices" / "TEST.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": CACHE_SCHEMA_VERSION,
                        "priceMode": PRICE_MODE,
                        "range": "3y",
                        "rows": [price_row("2026-06-10", 100)],
                        "meta": {},
                    }
                ),
                encoding="utf-8",
            )
            provider = FakeProvider(cache_dir, [price_row("2026-06-10", 102)])

            result = provider.update_base_cache("TEST", target_date="2026-06-10")

            self.assertEqual(result.action, "rebuilt")
            self.assertEqual(provider.fetch_periods, [BASE_PERIOD])

    def test_legacy_adjusted_cache_upgrades_metadata_without_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            path = cache_dir / "prices" / "TEST.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "symbol": "TEST",
                        "range": BASE_PERIOD,
                        "rows": [price_row("2026-06-10", 100)],
                        "meta": {},
                    }
                ),
                encoding="utf-8",
            )
            provider = FakeProvider(cache_dir, [price_row("2026-06-10", 101)])

            result = provider.update_base_cache("TEST", target_date="2026-06-10")
            upgraded = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(result.action, "skipped")
            self.assertEqual(provider.fetch_periods, [])
            self.assertEqual(upgraded["schemaVersion"], CACHE_SCHEMA_VERSION)
            self.assertEqual(upgraded["priceMode"], PRICE_MODE)

    def test_new_corporate_action_triggers_full_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = CorporateActionProvider(
                Path(tmp), [price_row("2026-06-10", 102)]
            )
            provider._write_base_cache("TEST", [price_row("2026-06-09", 100)], {})

            result = provider.update_base_cache("TEST", target_date="2026-06-10")

            self.assertEqual(result.action, "rebuilt")
            self.assertEqual(provider.fetch_periods, ["1mo", BASE_PERIOD])

    def test_retryable_http_error_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = YahooChartProvider(
                Path(tmp), max_retries=3, retry_delays=(0, 0, 0)
            )
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{"chart": {}}'
            error = HTTPError("https://example.test", 502, "bad gateway", {}, None)

            with patch(
                "stock_analyzer.data.urlopen",
                side_effect=[error, error, response],
            ) as mocked_urlopen:
                payload = provider._fetch("TEST", "1mo")

            self.assertEqual(payload, {"chart": {}})
            self.assertEqual(mocked_urlopen.call_count, 3)


if __name__ == "__main__":
    unittest.main()
