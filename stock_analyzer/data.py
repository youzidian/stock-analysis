from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .analysis import PriceRow


INTERVAL_TO_RANGE = {
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "2y": "2y",
    "3y": "3y",
    "5y": "5y",
    "10y": "10y",
}

BASE_PERIOD = "10y"
INCREMENTAL_PERIOD = "1mo"
CACHE_SCHEMA_VERSION = 3
PRICE_MODE = "raw+adjusted"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
PERIOD_DAYS = {
    "1mo": 31,
    "3mo": 93,
    "6mo": 186,
    "1y": 366,
    "2y": 366 * 2,
    "3y": 366 * 3,
    "5y": 366 * 5,
    "10y": 366 * 10,
}


class MarketDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class CacheRefresh:
    rows: list[PriceRow]
    meta: dict[str, object]
    action: str
    last_trading_date: str


class YahooChartProvider:
    def __init__(
        self,
        cache_dir: Path | str = ".cache",
        ttl_seconds: int = 900,
        max_retries: int = 3,
        retry_delays: tuple[float, ...] = (2.0, 5.0, 10.0),
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.max_retries = max(1, max_retries)
        self.retry_delays = retry_delays
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def history(
        self, symbol: str, period: str = "1y", force_refresh: bool = False
    ) -> list[PriceRow]:
        rows, _ = self.history_with_meta(symbol, period, force_refresh)
        return rows

    def history_with_meta(
        self, symbol: str, period: str = "1y", force_refresh: bool = False
    ) -> tuple[list[PriceRow], dict[str, object]]:
        normalized = symbol.strip().upper()
        if not normalized:
            raise MarketDataError("Please enter a stock symbol")
        if period not in INTERVAL_TO_RANGE:
            raise MarketDataError(f"Unsupported period: {period}")

        if force_refresh:
            rows, meta = self.refresh_base_cache(normalized, full=True)
        else:
            cached = self._read_base_cache(normalized, ignore_ttl=True)
            if cached is None or self.cache_needs_rebuild(normalized):
                rows, meta = self.refresh_base_cache(normalized, full=True)
            else:
                rows, meta = cached

        return _slice_rows(rows, period), meta

    def refresh_base_cache(
        self, symbol: str, full: bool = False
    ) -> tuple[list[PriceRow], dict[str, object]]:
        refreshed = self.update_base_cache(symbol, full=full)
        return refreshed.rows, refreshed.meta

    def update_base_cache(
        self,
        symbol: str,
        full: bool = False,
        target_date: str | None = None,
    ) -> CacheRefresh:
        normalized = symbol.strip().upper()
        cached = None if full else self._read_base_cache(normalized, ignore_ttl=True)
        if cached is not None and self.cache_needs_rebuild(normalized):
            cached = None
        elif cached is not None and self.cache_metadata_needs_upgrade(normalized):
            self._write_base_cache(normalized, cached[0], cached[1])
        if cached is not None and target_date:
            last_date = _last_trading_date(cached[0])
            if last_date and last_date >= target_date:
                return CacheRefresh(cached[0], cached[1], "skipped", last_date)

        fetch_period = BASE_PERIOD if cached is None else INCREMENTAL_PERIOD
        payload = self._fetch(normalized, fetch_period)
        corporate_action_rebuild = bool(
            cached is not None
            and _has_new_corporate_actions(payload, _last_trading_date(cached[0]))
        )
        if corporate_action_rebuild:
            payload = self._fetch(normalized, BASE_PERIOD)
        fetched_rows, meta = self._parse_chart(payload)
        if not fetched_rows:
            raise MarketDataError(f"{normalized} has no available market data")
        rows = (
            fetched_rows
            if cached is None or corporate_action_rebuild
            else _merge_rows(cached[0], fetched_rows)
        )
        rows = _trim_rows(rows, PERIOD_DAYS[BASE_PERIOD])
        self._write_base_cache(normalized, rows, meta)
        return CacheRefresh(
            rows,
            meta,
            "rebuilt" if cached is None or corporate_action_rebuild else "updated",
            _last_trading_date(rows),
        )

    def latest_trading_date(self, symbol: str) -> str:
        payload = self._fetch(symbol.strip().upper(), INCREMENTAL_PERIOD)
        rows, _ = self._parse_chart(payload)
        if not rows:
            raise MarketDataError(f"{symbol} has no recent market data")
        return _last_trading_date(rows)

    def cached_history_with_meta(
        self, symbol: str, period: str = BASE_PERIOD
    ) -> tuple[list[PriceRow], dict[str, object]]:
        normalized = symbol.strip().upper()
        cached = self._read_base_cache(normalized, ignore_ttl=True)
        if cached is None:
            raise MarketDataError(f"{normalized} has no local cache")
        if self.cache_needs_rebuild(normalized):
            raise MarketDataError(f"{normalized} local cache schema is outdated")
        return _slice_rows(cached[0], period), cached[1]

    def cache_needs_rebuild(self, symbol: str) -> bool:
        payload = self._read_base_payload(symbol)
        if payload is None:
            return True
        rows = payload.get("rows", [])
        schema_version = payload.get("schemaVersion")
        price_mode = payload.get("priceMode")
        return (
            (schema_version is not None and schema_version != CACHE_SCHEMA_VERSION)
            or (price_mode is not None and price_mode != PRICE_MODE)
            or payload.get("range") != BASE_PERIOD
            or not isinstance(rows, list)
            or not _has_adjusted_close(rows)
        )

    def cache_metadata_needs_upgrade(self, symbol: str) -> bool:
        payload = self._read_base_payload(symbol)
        return bool(
            payload is not None
            and not self.cache_needs_rebuild(symbol)
            and (
                payload.get("schemaVersion") != CACHE_SCHEMA_VERSION
                or payload.get("priceMode") != PRICE_MODE
                or not payload.get("lastTradingDate")
            )
        )

    def _fetch(self, symbol: str, period: str) -> dict[str, object]:
        params = urlencode(
            {
                "range": INTERVAL_TO_RANGE[period],
                "interval": "1d",
                "includePrePost": "false",
                "events": "div,splits",
            }
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"
        request = Request(url, headers={"User-Agent": "stock-analysis-local/0.1"})
        for attempt in range(self.max_retries):
            try:
                with urlopen(request, timeout=20) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code not in RETRYABLE_HTTP_CODES or attempt == self.max_retries - 1:
                    raise MarketDataError(f"Market data service returned HTTP {exc.code}") from exc
                self._retry_sleep(attempt)
            except URLError as exc:
                if attempt == self.max_retries - 1:
                    raise MarketDataError(f"Could not connect to the market data service: {exc.reason}") from exc
                self._retry_sleep(attempt)
            except TimeoutError as exc:
                if attempt == self.max_retries - 1:
                    raise MarketDataError("Market data request timed out") from exc
                self._retry_sleep(attempt)
        raise MarketDataError("Market data request failed")

    def _retry_sleep(self, attempt: int) -> None:
        base_delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
        time.sleep(base_delay + random.uniform(0, min(0.5, base_delay * 0.1)))

    def _parse_chart(self, payload: dict[str, object]) -> tuple[list[PriceRow], dict[str, object]]:
        chart = payload.get("chart", {})
        if not isinstance(chart, dict):
            raise MarketDataError("Unexpected market data response format")
        error = chart.get("error")
        if error:
            raise MarketDataError(str(error))
        results = chart.get("result")
        if not isinstance(results, list) or not results:
            return [], {}

        result = results[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp", [])
        indicators = result.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]
        adjusted_quotes = indicators.get("adjclose", [{}])
        adjusted_quote = adjusted_quotes[0] if adjusted_quotes else {}
        rows: list[PriceRow] = []
        for idx, timestamp in enumerate(timestamps):
            close = _pick(quote, "close", idx)
            if close is None:
                continue
            adjusted_close = _pick(adjusted_quote, "adjclose", idx)
            rows.append(
                {
                    "date": time.strftime("%Y-%m-%d", time.gmtime(int(timestamp))),
                    "open": _pick(quote, "open", idx) or close,
                    "high": _pick(quote, "high", idx) or close,
                    "low": _pick(quote, "low", idx) or close,
                    "close": close,
                    "adj_close": adjusted_close if adjusted_close is not None else close,
                    "volume": _pick(quote, "volume", idx) or 0,
                }
            )
        return rows, meta if isinstance(meta, dict) else {}

    def _cache_path(self, symbol: str, period: str) -> Path:
        safe_symbol = symbol.replace("/", "-")
        return self.cache_dir / f"{safe_symbol}_{period}.json"

    def _base_cache_path(self, symbol: str) -> Path:
        safe_symbol = symbol.replace("/", "-")
        return self.cache_dir / "prices" / f"{safe_symbol}.json"

    def _read_base_cache(
        self, symbol: str, ignore_ttl: bool = False
    ) -> tuple[list[PriceRow], dict[str, object]] | None:
        path = self._base_cache_path(symbol)
        if not path.exists():
            if ignore_ttl:
                return None
            return self._read_legacy_cache(symbol)
        if not ignore_ttl and time.time() - path.stat().st_mtime > self.ttl_seconds:
            legacy = self._read_legacy_cache(symbol)
            if legacy is not None:
                return legacy
            return None
        payload = self._read_base_payload(symbol)
        if payload is None:
            return None
        return payload.get("rows", []), payload.get("meta", {})

    def _read_base_payload(self, symbol: str) -> dict[str, object] | None:
        path = self._base_cache_path(symbol)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _read_legacy_cache(self, symbol: str) -> tuple[list[PriceRow], dict[str, object]] | None:
        path = self._cache_path(symbol, "1y")
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload.get("rows", []), payload.get("meta", {})
        return payload, {}

    def _write_base_cache(
        self, symbol: str, rows: list[PriceRow], meta: dict[str, object]
    ) -> None:
        path = self._base_cache_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": CACHE_SCHEMA_VERSION,
                    "symbol": symbol,
                    "range": BASE_PERIOD,
                    "priceMode": PRICE_MODE,
                    "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "lastTradingDate": _last_trading_date(rows),
                    "rows": rows,
                    "meta": meta,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def _pick(data: dict[str, list[float | int | None]], key: str, idx: int) -> float | int | None:
    values = data.get(key, [])
    if idx >= len(values):
        return None
    return values[idx]


def _merge_rows(existing: list[PriceRow], fresh: list[PriceRow]) -> list[PriceRow]:
    merged = {str(row["date"]): row for row in existing}
    for row in fresh:
        merged[str(row["date"])] = row
    return [merged[key] for key in sorted(merged)]


def _has_adjusted_close(rows: list[PriceRow]) -> bool:
    return bool(rows) and all("adj_close" in row for row in rows)


def _last_trading_date(rows: list[PriceRow]) -> str:
    return str(rows[-1]["date"]) if rows else ""


def _has_new_corporate_actions(payload: dict[str, object], last_date: str) -> bool:
    chart = payload.get("chart", {})
    results = chart.get("result", []) if isinstance(chart, dict) else []
    if not isinstance(results, list) or not results:
        return False
    events = results[0].get("events", {})
    if not isinstance(events, dict):
        return False
    for event_type in ("dividends", "splits"):
        event_map = events.get(event_type, {})
        if not isinstance(event_map, dict):
            continue
        for event in event_map.values():
            if not isinstance(event, dict):
                continue
            timestamp = event.get("date")
            if timestamp is None:
                continue
            event_date = time.strftime("%Y-%m-%d", time.gmtime(int(timestamp)))
            if event_date > last_date:
                return True
    return False


def _trim_rows(rows: list[PriceRow], days: int) -> list[PriceRow]:
    if not rows:
        return rows
    cutoff = date.fromisoformat(str(rows[-1]["date"])) - timedelta(days=days)
    return [row for row in rows if date.fromisoformat(str(row["date"])) >= cutoff]


def _slice_rows(rows: list[PriceRow], period: str) -> list[PriceRow]:
    if period == BASE_PERIOD:
        return rows
    if period not in PERIOD_DAYS:
        return rows
    if not rows:
        return rows
    cutoff = date.fromisoformat(str(rows[-1]["date"])) - timedelta(days=PERIOD_DAYS[period])
    sliced = [row for row in rows if date.fromisoformat(str(row["date"])) >= cutoff]
    return sliced or rows
