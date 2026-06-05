from __future__ import annotations

from dataclasses import dataclass
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


def lrc_snapshot(rows: list[PriceRow], window: int = 200) -> LrcSnapshot:
    if window < 3:
        raise ValueError("LRC window must be at least 3")
    if len(rows) < window:
        raise ValueError(f"LRC needs at least {window} rows")

    closes = [_safe_float(row["close"]) for row in rows[-window:]]
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


def lrc_channel(rows: list[PriceRow], window: int = 200) -> list[dict[str, object]]:
    if window < 3:
        raise ValueError("LRC window must be at least 3")
    if len(rows) < window:
        raise ValueError(f"LRC needs at least {window} rows")

    window_rows = rows[-window:]
    closes_oldest_first = [_safe_float(row["close"]) for row in window_rows]
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
                "短中期趋势",
                "多头排列" if trend_up else "未确认",
                "positive" if trend_up else "neutral",
                f"收盘价 {last_close:.2f}，20日均线 {sma20_value:.2f}，50日均线 {sma50_value:.2f}",
            )
        )

    if sma200_value:
        above = last_close > sma200_value
        signals.append(
            Signal(
                "长期位置",
                "站上200日线" if above else "低于200日线",
                "positive" if above else "negative",
                f"200日均线 {sma200_value:.2f}",
            )
        )

    if rsi_value is not None:
        if rsi_value >= 70:
            sentiment = "negative"
            value = "偏热"
        elif rsi_value <= 30:
            sentiment = "positive"
            value = "偏冷"
        else:
            sentiment = "neutral"
            value = "中性"
        signals.append(Signal("RSI(14)", value, sentiment, f"当前 RSI {rsi_value:.1f}"))

    if volume_avg:
        elevated = volume > volume_avg * 1.5
        signals.append(
            Signal(
                "成交量",
                "明显放量" if elevated else "常规",
                "positive" if elevated else "neutral",
                f"最新成交量是20日均量的 {volume / volume_avg:.2f} 倍",
            )
        )

    if high_52w and low_52w:
        distance_from_low = ((last_close - low_52w) / low_52w) * 100
        if drawdown > -8:
            sentiment = "positive"
            value = "接近高位"
        elif distance_from_low < 12:
            sentiment = "negative"
            value = "接近低位"
        else:
            sentiment = "neutral"
            value = "区间中部"
        signals.append(Signal("52周区间", value, sentiment, f"距52周高点 {drawdown:.1f}%"))

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
        label = "强势观察"
    elif points >= 55:
        label = "偏强"
    elif points >= 40:
        label = "中性"
    else:
        label = "偏弱"
    return {"value": points, "label": label}


def _safe_float(value: object) -> float:
    number = float(value or 0)
    return 0.0 if isnan(number) else number


def _safe_optional_float(value: object) -> float | None:
    if value is None:
        return None
    number = float(value)
    return None if isnan(number) else number
