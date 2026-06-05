from __future__ import annotations

import argparse
import csv
import json
import time
import zipfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .analysis import enrich_prices, lrc_snapshot
from .data import BASE_PERIOD, MarketDataError, YahooChartProvider


DEFAULT_SYMBOLS_FILE = Path("symbols.xlsx")
DEFAULT_BATCH_OUTPUT = Path(".cache/batch_results.json")
SIGMA_COLUMNS = [
    "代碼",
    "LRC Z-score",
    "名稱",
    "最新價",
    "漲跌額",
    "漲跌幅",
    "市值",
    "成交量",
    "成交額",
    "買入價",
    "賣出價",
    "MA-MA200-日線",
    "RSI-RSI14-日線",
    "MA-MA50-日線",
    "營業利潤(TTM)",
    "買量",
    "賣量",
    "開市",
    "前收",
    "最高",
    "最低",
    "量比",
    "委比",
    "振幅",
    "市盈率(靜)",
    "換手率",
    "漲跌速率",
    "5分鐘漲跌幅",
    "5日漲跌幅",
    "10日漲跌幅",
    "20日漲跌幅",
    "60日漲跌幅",
    "120日漲跌幅",
    "250日漲跌幅",
    "年初至今",
    "所屬行業",
]
DISABLED_VALUES = {"0", "FALSE", "NO", "N", "DISABLED", "停用", "否"}
XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass(frozen=True)
class CacheResult:
    symbol: str
    period: str
    ok: bool
    rows: int = 0
    error: str = ""


@dataclass(frozen=True)
class SymbolRecord:
    symbol: str
    market: str = ""
    name: str = ""
    enabled: str = ""
    industry: str = ""
    tags: tuple[str, ...] = ()
    notes: str = ""


def load_symbols(
    path: Path, markets: set[str] | None = None, tags: set[str] | None = None
) -> list[str]:
    records = load_symbol_records(path)
    return _dedupe(
        [
            record.symbol
            for record in records
            if _matches_filters(record, markets=markets, tags=tags)
        ]
    )


def load_symbol_records(path: Path) -> list[SymbolRecord]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _load_records_from_xlsx(path)
    if suffix == ".csv":
        return _load_records_from_csv(path)
    return [
        SymbolRecord(symbol=symbol)
        for symbol in _dedupe(_load_symbols_from_text(path))
    ]


def _load_symbols_from_text(path: Path) -> list[str]:
    symbols: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        symbol = raw_line.split("#", 1)[0].strip().upper()
        if symbol:
            symbols.append(symbol)
    return symbols


def _load_records_from_csv(path: Path) -> list[SymbolRecord]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        has_header = csv.Sniffer().has_header(sample) if sample.strip() else False
        if has_header:
            reader = csv.DictReader(handle)
            return [_record_from_mapping(row) for row in reader if _row_enabled(row)]
        reader = csv.reader(handle)
        return [
            SymbolRecord(symbol=row[0].strip().upper())
            for row in reader
            if row and row[0].strip()
        ]


def _load_records_from_xlsx(path: Path) -> list[SymbolRecord]:
    records: list[SymbolRecord] = []
    for sheet_name, rows in _read_xlsx_sheets(path):
        records.extend(_records_from_sheet(sheet_name, rows))
    return records


def _records_from_sheet(sheet_name: str, rows: list[list[str]]) -> list[SymbolRecord]:
    if not rows:
        return []
    header = [cell.strip().lower() for cell in rows[0]]
    if "symbol" not in header:
        return [
            SymbolRecord(symbol=row[0].strip().upper(), market=sheet_name.upper())
            for row in rows
            if row and row[0].strip()
        ]

    records: list[SymbolRecord] = []
    sheet_market = sheet_name.strip().upper()
    for row in rows[1:]:
        values = {
            column: row[idx].strip() if idx < len(row) else ""
            for idx, column in enumerate(header)
        }
        if not _row_enabled(values):
            continue
        if not values.get("market") or sheet_market != "SYMBOLS":
            values["market"] = sheet_market
        record = _record_from_mapping(values)
        if record.symbol:
            records.append(record)
    return records


def _read_xlsx_sheets(path: Path) -> list[tuple[str, list[list[str]]]]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        sheets = []
        for sheet_name, sheet_path in _sheet_paths(workbook):
            sheet_xml = workbook.read(sheet_path)
            sheets.append((sheet_name, _parse_sheet_rows(sheet_xml, shared_strings)))
    return sheets


def _parse_sheet_rows(sheet_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ElementTree.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row in root.findall(".//a:sheetData/a:row", XLSX_NS):
        values: list[str] = []
        current_col = 0
        for cell in row.findall("a:c", XLSX_NS):
            ref = cell.attrib.get("r", "")
            col_idx = _column_index(ref)
            if col_idx is not None:
                while current_col < col_idx:
                    values.append("")
                    current_col += 1
            values.append(_cell_value(cell, shared_strings))
            current_col += 1
        rows.append(values)
    return rows


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        xml = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(xml)
    strings: list[str] = []
    for item in root.findall("a:si", XLSX_NS):
        parts = [node.text or "" for node in item.findall(".//a:t", XLSX_NS)]
        strings.append("".join(parts))
    return strings


def _sheet_paths(workbook: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    sheet_nodes = workbook_root.findall(".//a:sheets/a:sheet", XLSX_NS)
    if not sheet_nodes:
        raise ValueError("Workbook has no sheets")

    rels_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib.get("Id"): rel.attrib.get("Target", "")
        for rel in rels_root
    }
    sheets: list[tuple[str, str]] = []
    for sheet in sheet_nodes:
        rel_id = sheet.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        target = rel_targets.get(rel_id)
        if not target:
            continue
        normalized_target = target.lstrip("/")
        path = normalized_target if normalized_target.startswith("xl/") else f"xl/{normalized_target}"
        sheets.append((sheet.attrib.get("name", ""), path))
    if not sheets:
        raise ValueError("Could not resolve worksheets")
    return sheets


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value_node = cell.find("a:v", XLSX_NS)
    if value_node is None or value_node.text is None:
        inline = cell.find("a:is/a:t", XLSX_NS)
        return inline.text if inline is not None and inline.text else ""

    value = value_node.text
    if cell.attrib.get("t") == "s":
        idx = int(value)
        return shared_strings[idx] if idx < len(shared_strings) else ""
    return value


def _column_index(cell_ref: str) -> int | None:
    letters = ""
    for char in cell_ref:
        if char.isalpha():
            letters += char.upper()
        else:
            break
    if not letters:
        return None
    idx = 0
    for char in letters:
        idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx - 1


def _row_enabled(row: dict[str, str]) -> bool:
    enabled = (row.get("enabled") or "").strip().upper()
    return enabled not in DISABLED_VALUES


def _record_from_mapping(row: dict[str, str]) -> SymbolRecord:
    return SymbolRecord(
        symbol=(row.get("symbol") or "").strip().upper(),
        market=(row.get("market") or "").strip().upper(),
        name=(row.get("name") or "").strip(),
        enabled=(row.get("enabled") or "").strip(),
        industry=(row.get("industry") or row.get("所屬行業") or "").strip(),
        tags=tuple(_split_tags(row.get("tags") or "")),
        notes=(row.get("notes") or "").strip(),
    )


def _split_tags(value: str) -> list[str]:
    normalized = value.replace(";", ",").replace("|", ",")
    return [tag.strip().upper() for tag in normalized.split(",") if tag.strip()]


def _matches_filters(
    record: SymbolRecord,
    markets: set[str] | None = None,
    tags: set[str] | None = None,
) -> bool:
    if markets and record.market.upper() not in markets:
        return False
    if tags and not tags.intersection(record.tags):
        return False
    return True


def parse_filter_values(value: str) -> set[str] | None:
    values = {item.strip().upper() for item in value.split(",") if item.strip()}
    return values or None


def _dedupe(symbols: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def refresh_cache(
    symbols: list[str],
    cache_dir: Path,
    delay_seconds: float = 0.25,
    full_refresh: bool = False,
) -> list[CacheResult]:
    provider = YahooChartProvider(cache_dir=cache_dir, ttl_seconds=0)
    results: list[CacheResult] = []

    for symbol in symbols:
        try:
            rows, _ = provider.refresh_base_cache(symbol, full=full_refresh)
            results.append(CacheResult(symbol, "3y", True, len(rows)))
        except MarketDataError as exc:
            results.append(CacheResult(symbol, "3y", False, error=str(exc)))
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return results


def build_batch_snapshot(
    records: list[SymbolRecord],
    cache_dir: Path,
    window: int = 200,
) -> dict[str, object]:
    provider = YahooChartProvider(cache_dir=cache_dir, ttl_seconds=10**9)
    results: list[dict[str, object]] = []

    for record in records:
        try:
            rows, meta = provider.history_with_meta(record.symbol, BASE_PERIOD)
            snapshot = lrc_snapshot(rows, window=window)
            enriched = enrich_prices(rows)
            latest = enriched[-1]
            fields = sigma_fields(record, rows, enriched, meta, snapshot.z_score)
            results.append(
                {
                    "symbol": record.symbol,
                    "market": record.market,
                    "name": record.name,
                    "industry": record.industry,
                    "tags": list(record.tags),
                    "ok": True,
                    "fields": fields,
                    "date": latest["date"],
                    "close": snapshot.latest_close,
                    "zScore": snapshot.z_score,
                    "trend": snapshot.trend,
                    "residual": snapshot.residual,
                    "stddev": snapshot.stddev,
                    "slope": snapshot.slope,
                    "window": snapshot.window,
                }
            )
        except (MarketDataError, ValueError) as exc:
            results.append(
                {
                    "symbol": record.symbol,
                    "market": record.market,
                    "name": record.name,
                    "industry": record.industry,
                    "tags": list(record.tags),
                    "ok": False,
                    "error": str(exc),
                    "fields": {"代碼": record.symbol, "名稱": record.name},
                }
            )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "window": window,
        "basePeriod": BASE_PERIOD,
        "columns": SIGMA_COLUMNS,
        "count": len({record.symbol for record in records}),
        "results": results,
    }


def sigma_fields(
    record: SymbolRecord,
    rows: list[dict[str, object]],
    enriched: list[dict[str, object]],
    meta: dict[str, object],
    z_score: float,
) -> dict[str, object]:
    latest = enriched[-1]
    previous = enriched[-2] if len(enriched) > 1 else latest
    latest_close = _num(latest.get("close"))
    previous_close = _num(previous.get("close"))
    change = latest_close - previous_close
    change_pct = (change / previous_close * 100) if previous_close else None
    volume = _num(latest.get("volume"))
    amount = latest_close * volume if latest_close is not None and volume is not None else None
    high = _num(latest.get("high"))
    low = _num(latest.get("low"))
    amplitude = ((high - low) / previous_close * 100) if high is not None and low is not None and previous_close else None
    volume_sma20 = _num(latest.get("volume_sma20"))
    volume_ratio = volume / volume_sma20 if volume is not None and volume_sma20 else None

    return {
        "代碼": record.symbol,
        "LRC Z-score": z_score,
        "名稱": record.name or str(meta.get("longName") or meta.get("shortName") or ""),
        "最新價": _num(meta.get("regularMarketPrice")) or latest_close,
        "漲跌額": change,
        "漲跌幅": change_pct,
        "市值": _num(meta.get("marketCap")),
        "成交量": _num(meta.get("regularMarketVolume")) or volume,
        "成交額": amount,
        "買入價": _num(meta.get("bid")),
        "賣出價": _num(meta.get("ask")),
        "MA-MA200-日線": _num(latest.get("sma200")),
        "RSI-RSI14-日線": _num(latest.get("rsi14")),
        "MA-MA50-日線": _num(latest.get("sma50")),
        "營業利潤(TTM)": None,
        "買量": None,
        "賣量": None,
        "開市": _num(latest.get("open")),
        "前收": previous_close,
        "最高": _num(meta.get("regularMarketDayHigh")) or high,
        "最低": _num(meta.get("regularMarketDayLow")) or low,
        "量比": volume_ratio,
        "委比": None,
        "振幅": amplitude,
        "市盈率(靜)": None,
        "換手率": None,
        "漲跌速率": change_pct,
        "5分鐘漲跌幅": None,
        "5日漲跌幅": period_change(rows, 5),
        "10日漲跌幅": period_change(rows, 10),
        "20日漲跌幅": period_change(rows, 20),
        "60日漲跌幅": period_change(rows, 60),
        "120日漲跌幅": period_change(rows, 120),
        "250日漲跌幅": period_change(rows, 250),
        "年初至今": year_to_date_change(rows),
        "所屬行業": record.industry or None,
    }


def period_change(rows: list[dict[str, object]], trading_days: int) -> float | None:
    if len(rows) <= trading_days:
        return None
    latest = _num(rows[-1].get("close"))
    base = _num(rows[-1 - trading_days].get("close"))
    if latest is None or not base:
        return None
    return (latest - base) / base * 100


def year_to_date_change(rows: list[dict[str, object]]) -> float | None:
    if not rows:
        return None
    latest = _num(rows[-1].get("close"))
    latest_year = str(rows[-1].get("date", ""))[:4]
    base = None
    for row in rows:
        if str(row.get("date", "")).startswith(latest_year):
            base = _num(row.get("close"))
            break
    if latest is None or not base:
        return None
    return (latest - base) / base * 100


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_batch_snapshot(snapshot: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_report(results: list[CacheResult], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "period", "ok", "rows", "error"])
        for result in results:
            writer.writerow(
                [result.symbol, result.period, result.ok, result.rows, result.error]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh local stock cache")
    parser.add_argument("--symbols-file", default=str(DEFAULT_SYMBOLS_FILE))
    parser.add_argument("--cache-dir", default=".cache")
    parser.add_argument("--delay", default=0.25, type=float)
    parser.add_argument("--report", default=".cache/cache_report.csv")
    parser.add_argument("--markets", default="", help="Comma-separated market filter")
    parser.add_argument("--tags", default="", help="Comma-separated tag filter")
    parser.add_argument("--lrc-window", default=200, type=int)
    parser.add_argument("--full-refresh", action="store_true")
    parser.add_argument("--batch-output", default=str(DEFAULT_BATCH_OUTPUT))
    parser.add_argument(
        "--skip-batch-snapshot",
        action="store_true",
        help="Only refresh raw price cache; do not write precomputed batch results",
    )
    args = parser.parse_args()

    symbols_path = Path(args.symbols_file)
    if not symbols_path.exists():
        raise SystemExit(f"Symbols file not found: {symbols_path}")

    markets = parse_filter_values(args.markets)
    tags = parse_filter_values(args.tags)
    records = [
        record
        for record in load_symbol_records(symbols_path)
        if _matches_filters(record, markets=markets, tags=tags)
    ]
    symbols = _dedupe([record.symbol for record in records])
    if not symbols:
        raise SystemExit(f"No symbols found in {symbols_path}")

    filter_parts = []
    if markets:
        filter_parts.append(f"markets={','.join(sorted(markets))}")
    if tags:
        filter_parts.append(f"tags={','.join(sorted(tags))}")
    filter_text = f" ({'; '.join(filter_parts)})" if filter_parts else ""
    print(f"Refreshing {len(symbols)} symbols{filter_text} into 3y base cache")
    results = refresh_cache(
        symbols, Path(args.cache_dir), args.delay, full_refresh=args.full_refresh
    )
    write_report(results, Path(args.report))

    if not args.skip_batch_snapshot:
        snapshot = build_batch_snapshot(
            records=records,
            cache_dir=Path(args.cache_dir),
            window=args.lrc_window,
        )
        write_batch_snapshot(snapshot, Path(args.batch_output))

    ok_count = sum(1 for result in results if result.ok)
    fail_count = len(results) - ok_count
    batch_text = "" if args.skip_batch_snapshot else f" batch={args.batch_output}"
    print(f"Done. success={ok_count} failed={fail_count} report={args.report}{batch_text}")
    if fail_count:
        print("Failed symbols:")
        for result in results:
            if not result.ok:
                print(f"- {result.symbol} {result.period}: {result.error}")


if __name__ == "__main__":
    main()
