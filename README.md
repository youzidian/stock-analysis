# Local Stock Analysis

A personal, locally hosted web app for stock research. It uses daily market data to build price charts, moving averages, RSI, 52-week range metrics, Linear Regression Channel Z-scores, Sigma Model screening, and MA Slope analysis.

This project is designed to run on Linux. It also works in WSL, but the commands below avoid machine-specific Windows paths.

## Features

- Local web server using Python's standard library
- Daily OHLCV data from Yahoo Finance's chart endpoint
- Ten-year local base cache per symbol
- Incremental daily cache updates when possible
- Sigma Model precomputed cross-section from `symbols.xlsx`
- Single-symbol analysis with price, MA, RSI, LRC, signals, and paginated history
- MA Slope analysis with configurable MA periods and slope lookback

## Requirements

- Linux or WSL
- Python 3.10 or newer
- Network access to Yahoo Finance for cache updates

No npm build step is required. The frontend is plain HTML, CSS, and JavaScript.

## Quick Start

From the project directory:

```sh
python3 --version
sh run.sh
```

Then open:

```text
http://127.0.0.1:8765
```

Run in the background:

```sh
sh run.sh start
```

Check status, restart, or stop:

```sh
sh run.sh status
sh run.sh restart
sh run.sh stop
```

Background logs are written to:

```text
.cache/server.log
```

If you want the app to listen on all network interfaces, use:

```sh
HOST=0.0.0.0 sh run.sh start
```

You can also choose another port:

```sh
PORT=9000 sh run.sh start
```

If Python is installed at a non-standard path:

```sh
PYTHON=/path/to/python3 sh run.sh start
```

## Symbols File

The stock universe is managed in:

```text
symbols.xlsx
```

Each worksheet represents a market, for example:

```text
US
HK
```

Each worksheet should contain these columns. Column order does not matter because the loader reads by column name:

```text
symbol | name | industry | enabled
```

Rows are skipped when `enabled` is one of:

```text
FALSE, 0, no, disabled
```

Example:

```text
US sheet
symbol   name          industry             enabled
AAPL     Apple         Consumer Electronics TRUE
MSFT     Microsoft     Software             TRUE
SPY      S&P 500 ETF   ETF                  TRUE

HK sheet
symbol   name          industry   enabled
0700.HK  Tencent       Internet   TRUE
9988.HK  Alibaba HK    E-commerce TRUE
```

Yahoo Finance uses the `.HK` suffix for many Hong Kong listings, such as `0700.HK`.

## Update The Cache

Refresh all enabled symbols:

```sh
sh update_cache.sh
```

The update process:

- Reads enabled symbols from `symbols.xlsx`
- Maintains one ten-year base cache per symbol under `.cache/prices/`
- Skips symbols that already match the target trading date
- Downloads a recent delta for stale symbols when possible
- Rebuilds missing, damaged, or outdated cache files
- Retries temporary errors such as 429, 500, 502, 503, 504, network errors, and timeouts
- Preserves the last successful cache when an update fails
- Writes a precomputed Sigma Model snapshot to `.cache/batch_results.json`

Useful update commands:

```sh
# Only update selected symbols
sh update_cache.sh --symbols AAPL,MSFT,0700.HK

# Retry only symbols that failed in the previous run
sh update_cache.sh --retry-failed

# Force a full rebuild for selected symbols
sh update_cache.sh --full-refresh --symbols AAPL

# Only update one market
MARKETS=US sh update_cache.sh
MARKETS=HK sh update_cache.sh

# Increase or reduce request delay
DELAY=0.5 sh update_cache.sh
```

Update reports are written to:

```text
.cache/cache_report.csv
.cache/failed_symbols.json
```

If you need to rebuild one local slice manually:

```sh
rm .cache/prices/VT.json
sh update_cache.sh --symbols VT
```

## Daily Automation

On Linux, edit the user's crontab:

```sh
crontab -e
```

Example: update every day at 07:30 local system time:

```cron
30 7 * * * cd /path/to/stock_analysis && mkdir -p .cache && /usr/bin/flock -n .cache/update_cache.lock /bin/sh update_cache.sh >> .cache/cron.log 2>&1
```

`flock` prevents a second update from starting while the previous one is still running.

Make sure cron is running on the target machine. The exact command depends on the Linux distribution, but common options are:

```sh
sudo systemctl status cron
sudo systemctl start cron
```

or:

```sh
sudo service cron status
sudo service cron start
```

## Analysis Logic

The Sigma Model `LRC Z-score` uses a 200-day Linear Regression Channel:

```text
(latest adjusted close - regression trend value) / regression residual standard deviation
```

LRC uses adjusted close to reduce discontinuities caused by dividends and splits. The displayed latest price, open, high, low, and daily change still use the raw Yahoo OHLC values.

MA Slope uses the local ten-year cache. Changing MA periods or slope lookback does not request Yahoo again.

Slope formula:

```text
(SMA_t / SMA_(t-N) - 1) * 100 / N
```

The unit is `% per trading day`.

## Tests

Run the test suite:

```sh
python3 -m unittest discover -s tests
```

Run a JavaScript syntax check if Node.js is available:

```sh
node --check web/app.js
```

## Notes

This tool is for research and record keeping only. It is not investment advice.

Yahoo Finance's chart endpoint is unofficial and best suited for personal, lightweight use. For a production-quality data feed, replace the provider implementation in `stock_analyzer/data.py`.
