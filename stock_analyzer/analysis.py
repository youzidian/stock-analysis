from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isnan
from statistics import mean


PriceRow = dict[str, float | int | str]


@dataclass(frozen=True)
class Signal:
    label: str
    value: str
    sentiment: str
    detail: str


@dataclass(frozen=True)
class LrcSnapshot:
    z_score: float
    latest_close: float
    trend: float
    residual: float
    stddev: float
    slope: float
    intercept: float
    window: int


def sma(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")

    output: list[float | None] = []
    running = 0.0
    for idx, value in enumerate(values):
        running += value
        if idx >= window:
            running -= values[idx - window]
        output.append(running / window if idx >= window - 1 else None)
    return output


def ema(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    if not values:
        return []

    alpha = 2 / (window + 1)
    output: list[float | None] = []
    current = values[0]
    for idx, value in enumerate(values):
        current = value if idx == 0 else alpha * value + (1 - alpha) * current
        output.append(current if idx >= window - 1 else None)
    return output


def rsi(values: list[float], window: int = 14) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < 2:
        return [None] * len(values)

    output: list[float | None] = [None] * len(values)
    gains: list[float] = []
    losses: list[float] = []

    for idx in range(1, len(values)):
        change = values[idx] - values[idx - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
        if idx < window:
            continue
        if idx == window:
            avg_gain = mean(gains[-window:])
            avg_loss = mean(losses[-window:])
        else:
            avg_gain = ((avg_gain * (window - 1)) + gains[-1]) / window
            avg_loss = ((avg_loss * (window - 1)) + losses[-1]) / window
        output[idx] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

    return output


def enrich_prices(rows: list[PriceRow]) -> list[PriceRow]:
    closes = [_safe_float(row["close"]) for row in rows]
    volumes = [_safe_float(row.get("volume", 0)) for row in rows]
    ma20 = sma(closes, 20)
    ma50 = sma(closes, 50)
    ma200 = sma(closes, 200)
    vol20 = sma(volumes, 20)
    rsi14 = rsi(closes, 14)

    enriched: list[PriceRow] = []
    for idx, row in enumerate(rows):
        previous = closes[idx - 1] if idx > 0 else None
        enriched_row = dict(row)
        enriched_row["change_pct"] = (
            ((closes[idx] - previous) / previous) * 100 if previous else 0.0
        )
        enriched_row["sma20"] = ma20[idx]
        enriched_row["sma50"] = ma50[idx]
        enriched_row["sma200"] = ma200[idx]
        enriched_row["volume_sma20"] = vol20[idx]
        enriched_row["rsi14"] = rsi14[idx]
        enriched.append(enriched_row)
    return enriched


def build_summary(symbol: str, rows: list[PriceRow]) -> dict[str, object]:
    if not rows:
        raise ValueError("No price rows available")

    enriched = enrich_prices(rows)
    lrc_z_scores = rolling_lrc_z_scores(rows)
    for row, z_score in zip(enriched, lrc_z_scores):
        row["lrc_zscore"] = z_score
    latest = enriched[-1]
    closes = [_safe_float(row["close"]) for row in enriched]
    highs = [_safe_float(row["high"]) for row in enriched]
    lows = [_safe_float(row["low"]) for row in enriched]
    last_close = _safe_float(latest["close"])
    first_close = closes[0]
    high_52w = max(highs[-252:]) if highs else last_close
    low_52w = min(lows[-252:]) if lows else last_close
    drawdown = ((last_close - high_52w) / high_52w) * 100 if high_52w else 0.0
    period_return = ((last_close - first_close) / first_close) * 100 if first_close else 0.0

    signals = _build_signals(latest, last_close, high_52w, low_52w, drawdown)
    score = _score(signals)

    return {
        "symbol": symbol.upper(),
        "latest": latest,
        "periodReturnPct": period_return,
        "high52w": high_52w,
        "low52w": low_52w,
        "drawdownPct": drawdown,
        "score": score,
        "signals": [signal.__dict__ for signal in signals],
        "lrc": lrc_channel(rows, window=min(200, len(rows))) if len(rows) >= 3 else [],
        "rows": enriched,
    }


def build_ma_slope_summary(
    symbol: str,
    rows: list[PriceRow],
    periods: list[int],
    slope_window: int,
    display_rows: int | None = None,
    display_start_date: date | None = None,
) -> dict[str, object]:
    if not rows:
        raise ValueError("No price rows available")
    if not periods or any(period <= 0 for period in periods):
        raise ValueError("MA periods must be positive integers")
    if slope_window <= 0:
        raise ValueError("Slope window must be positive")

    normalized_periods = sorted(set(periods))
    closes = [_safe_float(row["close"]) for row in rows]
    moving_averages = {
        period: sma(closes, period) for period in normalized_periods
    }
    slopes: dict[int, list[float | None]] = {}
    for period in normalized_periods:
        values = moving_averages[period]
        period_slopes: list[float | None] = []
        for idx, value in enumerate(values):
            previous_idx = idx - slope_window
            previous = values[previous_idx] if previous_idx >= 0 else None
            period_slopes.append(
                ((value / previous - 1) * 100 / slope_window)
                if value is not None and previous not in (None, 0)
                else None
            )
        slopes[period] = period_slopes

    if display_start_date is not None:
        start_idx = next(
            (
                idx
                for idx, row in enumerate(rows)
                if date.fromisoformat(str(row["date"])) >= display_start_date
            ),
            len(rows),
        )
    else:
        start_idx = max(0, len(rows) - display_rows) if display_rows else 0
    if start_idx >= len(rows):
        raise ValueError("No data in selected display window")
    output_rows: list[dict[str, object]] = []
    for idx, row in enumerate(rows[start_idx:], start=start_idx):
        output_rows.append(
            {
                "date": row["date"],
                "open": _safe_float(row["open"]),
                "high": _safe_float(row["high"]),
                "low": _safe_float(row["low"]),
                "close": closes[idx],
                "volume": _safe_float(row.get("volume", 0)),
                "mas": {
                    str(period): moving_averages[period][idx]
                    for period in normalized_periods
                },
                "slopes": {
                    str(period): slopes[period][idx]
                    for period in normalized_periods
                },
            }
        )

    latest = output_rows[-1]
    metrics = []
    statistics = []
    for period in normalized_periods:
        key = str(period)
        ma_value = latest["mas"][key]
        slope_value = latest["slopes"][key]
        valid_slopes = [
            (str(row["date"]), float(row["slopes"][key]))
            for row in output_rows
            if row["slopes"][key] is not None
        ]
        slope_values = [value for _, value in valid_slopes]
        percentile = (
            sum(value < float(slope_value) for value in slope_values)
            / len(slope_values)
            * 100
            if slope_value is not None and slope_values
            else None
        )
        metrics.append(
            {
                "period": period,
                "ma": ma_value,
                "priceVsMaPct": (
                    (float(ma_value) / float(latest["close"]) - 1) * 100
                    if ma_value not in (None, 0) and latest["close"]
                    else None
                ),
                "slope": slope_value,
                "percentile": percentile,
            }
        )
        statistics.append(
            {
                "period": period,
                "current": slope_value,
                "mean": mean(slope_values) if slope_values else None,
                "stddev": (
                    (
                        sum(
                            (value - mean(slope_values)) ** 2
                            for value in slope_values
                        )
                        / (len(slope_values) - 1)
                    )
                    ** 0.5
                    if len(slope_values) > 1
                    else None
                ),
                "min": min(slope_values) if slope_values else None,
                "minDate": (
                    min(valid_slopes, key=lambda item: item[1])[0]
                    if valid_slopes
                    else None
                ),
                "max": max(slope_values) if slope_values else None,
                "negativePct": (
                    sum(value < 0 for value in slope_values)
                    / len(slope_values)
                    * 100
                    if slope_values
                    else None
                ),
            }
        )

    return {
        "symbol": symbol.upper(),
        "periods": normalized_periods,
        "slopeWindow": slope_window,
        "latest": {
            "date": latest["date"],
            "close": latest["close"],
        },
        "metrics": metrics,
        "statistics": statistics,
        "rows": output_rows,
    }


def lrc_snapshot(rows: list[PriceRow], window: int = 200) -> LrcSnapshot:
    if window < 3:
        raise ValueError("LRC window must be at least 3")
    if len(rows) < window:
        raise ValueError(f"LRC needs at least {window} rows")

    closes = [_lrc_close(row) for row in rows[-window:]]
    newest_first = list(reversed(closes))
    xs = list(range(1, window + 1))
    x_mean = mean(xs)
    y_mean = mean(newest_first)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    slope_value = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, newest_first))
        / denominator
    )
    intercept_value = y_mean - slope_value * x_mean
    residuals = [
        y - (slope_value * x + intercept_value)
        for x, y in zip(xs, newest_first)
    ]
    stddev = (sum(residual * residual for residual in residuals) / (window - 1)) ** 0.5
    if stddev == 0:
        raise ValueError("LRC standard deviation is zero")

    latest_close = newest_first[0]
    trend = slope_value + intercept_value
    residual = latest_close - trend
    return LrcSnapshot(
        z_score=residual / stddev,
        latest_close=latest_close,
        trend=trend,
        residual=residual,
        stddev=stddev,
        slope=slope_value,
        intercept=intercept_value,
        window=window,
    )


def rolling_lrc_z_scores(
    rows: list[PriceRow], window: int = 200
) -> list[float | None]:
    if window < 3:
        raise ValueError("LRC window must be at least 3")

    output: list[float | None] = [None] * len(rows)
    for idx in range(window - 1, len(rows)):
        try:
            output[idx] = lrc_snapshot(rows[: idx + 1], window=window).z_score
        except ValueError as exc:
            if "standard deviation is zero" not in str(exc):
                raise
    return output


def lrc_channel(rows: list[PriceRow], window: int = 200) -> list[dict[str, object]]:
    if window < 3:
        raise ValueError("LRC window must be at least 3")
    if len(rows) < window:
        raise ValueError(f"LRC needs at least {window} rows")

    window_rows = rows[-window:]
    closes_oldest_first = [_lrc_close(row) for row in window_rows]
    newest_first = list(reversed(closes_oldest_first))
    xs = list(range(1, window + 1))
    x_mean = mean(xs)
    y_mean = mean(newest_first)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    slope_value = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, newest_first))
        / denominator
    )
    intercept_value = y_mean - slope_value * x_mean
    residuals = [
        y - (slope_value * x + intercept_value)
        for x, y in zip(xs, newest_first)
    ]
    stddev = (sum(residual * residual for residual in residuals) / (window - 1)) ** 0.5

    channel_newest_first = []
    for row, close, x_value in zip(reversed(window_rows), newest_first, xs):
        trend = slope_value * x_value + intercept_value
        channel_newest_first.append(
            {
                "date": row["date"],
                "close": close,
                "trend": trend,
                "upper2": trend + 2 * stddev,
                "lower2": trend - 2 * stddev,
                "upper4": trend + 4 * stddev,
                "lower4": trend - 4 * stddev,
            }
        )
    return list(reversed(channel_newest_first))


def _build_signals(
    latest: PriceRow, last_close: float, high_52w: float, low_52w: float, drawdown: float
) -> list[Signal]:
    signals: list[Signal] = []
    sma20_value = _safe_optional_float(latest.get("sma20"))
    sma50_value = _safe_optional_float(latest.get("sma50"))
    sma200_value = _safe_optional_float(latest.get("sma200"))
    rsi_value = _safe_optional_float(latest.get("rsi14"))
    volume = _safe_float(latest.get("volume", 0))
    volume_avg = _safe_optional_float(latest.get("volume_sma20"))

    if sma20_value and sma50_value:
        trend_up = last_close > sma20_value > sma50_value
        signals.append(
            Signal(
                "Short/Mid-Term Trend",
                "Bullish alignment" if trend_up else "Not confirmed",
                "positive" if trend_up else "neutral",
                f"Close {last_close:.2f}, 20-day MA {sma20_value:.2f}, 50-day MA {sma50_value:.2f}",
            )
        )

    if sma200_value:
        above = last_close > sma200_value
        signals.append(
            Signal(
                "Long-Term Position",
                "Above 200-day MA" if above else "Below 200-day MA",
                "positive" if above else "negative",
                f"200-day MA {sma200_value:.2f}",
            )
        )

    if rsi_value is not None:
        if rsi_value >= 70:
            sentiment = "negative"
            value = "Hot"
        elif rsi_value <= 30:
            sentiment = "positive"
            value = "Cold"
        else:
            sentiment = "neutral"
            value = "Neutral"
        signals.append(Signal("RSI(14)", value, sentiment, f"Current RSI {rsi_value:.1f}"))

    if volume_avg:
        elevated = volume > volume_avg * 1.5
        signals.append(
            Signal(
                "Volume",
                "Elevated" if elevated else "Normal",
                "positive" if elevated else "neutral",
                f"Latest volume is {volume / volume_avg:.2f}x the 20-day average",
            )
        )

    if high_52w and low_52w:
        distance_from_low = ((last_close - low_52w) / low_52w) * 100
        if drawdown > -8:
            sentiment = "positive"
            value = "Near high"
        elif distance_from_low < 12:
            sentiment = "negative"
            value = "Near low"
        else:
            sentiment = "neutral"
            value = "Mid range"
        signals.append(Signal("52W Range", value, sentiment, f"{drawdown:.1f}% from the 52-week high"))

    return signals


def _score(signals: list[Signal]) -> dict[str, object]:
    points = 50
    for signal in signals:
        if signal.sentiment == "positive":
            points += 10
        elif signal.sentiment == "negative":
            points -= 10
    points = max(0, min(100, points))
    if points >= 70:
        label = "Strong watch"
    elif points >= 55:
        label = "Moderately strong"
    elif points >= 40:
        label = "Neutral"
    else:
        label = "Weak"
    return {"value": points, "label": label}


def _safe_float(value: object) -> float:
    number = float(value or 0)
    return 0.0 if isnan(number) else number


def _lrc_close(row: PriceRow) -> float:
    return _safe_float(row.get("adj_close", row["close"]))


def _safe_optional_float(value: object) -> float | None:
    if value is None:
        return None
    number = float(value)
    return None if isnan(number) else number
