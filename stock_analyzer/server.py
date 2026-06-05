from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .analysis import build_summary
from .cache_builder import build_batch_snapshot, load_symbol_records, parse_filter_values
from .data import MarketDataError, YahooChartProvider


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
PROVIDER = YahooChartProvider(ROOT / ".cache")
BATCH_RESULTS_PATH = ROOT / ".cache" / "batch_results.json"


class StockAnalysisHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self._handle_analyze(parsed.query)
            return
        if parsed.path == "/api/batch":
            self._handle_batch(parsed.query)
            return
        if parsed.path == "/health":
            self._json({"ok": True})
            return
        super().do_GET()

    def _handle_analyze(self, query: str) -> None:
        params = parse_qs(query)
        symbol = params.get("symbol", ["AAPL"])[0]
        period = params.get("period", ["1y"])[0]
        try:
            rows = PROVIDER.history(symbol, period)
            self._json(build_summary(symbol, rows))
        except (MarketDataError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._json({"error": f"分析失败: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_batch(self, query: str) -> None:
        params = parse_qs(query)
        markets = parse_filter_values(params.get("markets", [""])[0])
        refresh = params.get("refresh", ["0"])[0] in {"1", "true", "TRUE"}

        try:
            if refresh or not BATCH_RESULTS_PATH.exists():
                payload = self._compute_batch_live(markets)
                payload["source"] = "live"
                self._json(payload)
                return

            snapshot = json.loads(BATCH_RESULTS_PATH.read_text(encoding="utf-8"))
            results = [
                row
                for row in snapshot.get("results", [])
                if _matches_market(row, markets)
            ]
            results.sort(
                key=lambda row: (
                    not bool(row.get("ok")),
                    float(row.get("zScore", 0)) if row.get("ok") else 0,
                )
            )
            self._json(
                {
                    "symbolsFile": "symbols.xlsx" if (ROOT / "symbols.xlsx").exists() else "symbols.txt",
                    "source": "precomputed",
                    "generatedAt": snapshot.get("generatedAt"),
                    "window": snapshot.get("window"),
                    "columns": snapshot.get("columns", []),
                    "availableMarkets": sorted(
                        {
                            str(row.get("market", "")).upper()
                            for row in snapshot.get("results", [])
                            if row.get("market")
                        }
                    ),
                    "count": len(results),
                    "markets": sorted(markets) if markets else [],
                    "results": results,
                }
            )
        except Exception as exc:
            self._json({"error": f"批量分析失败: {exc}"}, HTTPStatus.BAD_REQUEST)

    def _compute_batch_live(
        self,
        markets: set[str] | None,
    ) -> dict[str, object]:
        symbols_path = ROOT / "symbols.xlsx"
        if not symbols_path.exists():
            symbols_path = ROOT / "symbols.txt"

        records = [
            record
            for record in load_symbol_records(symbols_path)
            if _matches_record_market(record.market, markets)
        ]
        snapshot = build_batch_snapshot(records, ROOT / ".cache")
        results = list(snapshot.get("results", []))
        results.sort(
            key=lambda row: (
                not bool(row.get("ok")),
                float(row.get("zScore", 0)) if row.get("ok") else 0,
            )
        )
        return {
            "symbolsFile": str(symbols_path.name),
            "generatedAt": snapshot.get("generatedAt"),
            "window": snapshot.get("window"),
            "columns": snapshot.get("columns", []),
            "availableMarkets": sorted(
                {str(row.get("market", "")).upper() for row in results if row.get("market")}
            ),
            "count": len(results),
            "markets": sorted(markets) if markets else [],
            "results": results,
        }

    def _json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local stock analysis app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), StockAnalysisHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Stock analysis app running at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()


def _matches_market(row: dict[str, object], markets: set[str] | None) -> bool:
    if not markets:
        return True
    return str(row.get("market", "")).upper() in markets


def _matches_record_market(market: str, markets: set[str] | None) -> bool:
    if not markets:
        return True
    return market.upper() in markets
