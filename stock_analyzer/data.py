from __future__ import annotations

import json
import time
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
}

BASE_PERIOD = "3y"
INCREMENTAL_PERIOD = "1mo"
PERIOD_DAYS = {
    "1mo": 31,
    "3mo": 93,
    "6mo": 186,
    "1y": 366,
    "2y": 366 * 2,
    "3y": 366 * 3,
}


class MarketDataError(RuntimeError):
    pass


class YahooChartProvider:
    def __init__(self, cache_dir: Path | str = ".cache", ttl_seconds: int = 900) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
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
            raise MarketDataError("请输入股票代码")
        if period not in INTERVAL_TO_RANGE:
            raise MarketDataError(f"Unsupported period: {period}")

        if force_refresh:
            rows, meta = self.refresh_base_cache(normalized, full=True)
        else:
            cached = self._read_base_cache(normalized)
            if cached is None:
                rows, meta = self.refresh_base_cache(normalized, full=True)
            else:
                rows, meta = cached

        return _slice_rows(rows, period), meta

    def refresh_base_cache(self, symbol: str, full: bool = False) -> tuple[list[PriceRow], dict[str, object]]:
        normalized = symbol.strip().upper()
        cached = None if full else self._read_base_cache(normalized, ignore_ttl=True)
        fetch_period = BASE_PERIOD if cached is None else INCREMENTAL_PERIOD
        payload = self._fetch(normalized, fetch_period)
        fetched_rows, meta = self._parse_chart(payload)
        if not fetched_rows:
            raise MarketDataError(f"{normalized} 没有可用行情数据")
        rows = fetched_rows if cached is None else _merge_rows(cached[0], fetched_rows)
        rows = _trim_rows(rows, PERIOD_DAYS[BASE_PERIOD])
        self._write_base_cache(normalized, rows, meta)
        return rows, meta

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
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise MarketDataError(f"行情服务返回 HTTP {exc.code}") from exc
        except URLError as exc:
            raise MarketDataError(f"无法连接行情服务: {exc.reason}") from exc
        except TimeoutError as exc:
            raise MarketDataError("行情请求超时") from exc

    def _parse_chart(self, payload: dict[str, object]) -> tuple[list[PriceRow], dict[str, object]]:
        chart = payload.get("chart", {})
        if not isinstance(chart, dict):
            raise MarketDataError("行情响应格式异常")
        error = chart.get("error")
        if error:
            raise MarketDataError(str(error))
        results = chart.get("result")
        if not isinstance(results, list) or not results:
            return [], {}

        result = results[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        rows: list[PriceRow] = []
        for idx, timestamp in enumerate(timestamps):
            close = _pick(quote, "close", idx)
            if close is None:
                continue
            rows.append(
                {
                    "date": time.strftime("%Y-%m-%d", time.gmtime(int(timestamp))),
                    "open": _pick(quote, "open", idx) or close,
                    "high": _pick(quote, "high", idx) or close,
                    "low": _pick(quote, "low", idx) or close,
                    "close": close,
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
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("rows", []), payload.get("meta", {})

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
                    "symbol": symbol,
                    "range": BASE_PERIOD,
                    "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
