from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from math import ceil
from math import cos
from math import pi
from math import sin
from statistics import mean
from statistics import pstdev

import polars as pl
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing


@dataclass(slots=True)
class ForecastPoint:
    week: str
    predicted: float
    minimum: float
    maximum: float
    scenario: str


def _week_of_year_factor(value: date) -> tuple[float, float]:
    week = value.isocalendar().week
    angle = 2 * pi * (week / 52.0)
    return sin(angle), cos(angle)


def _series_rows(series: pl.DataFrame) -> list[dict]:
    rows = (
        series.sort("week")
        .select("week", "avg_price", "avg_buy_price", "dollar", "brent", "ipca")
        .to_dicts()
    )
    for row in rows:
        if isinstance(row["week"], datetime):
            row["week"] = row["week"].date()
        elif isinstance(row["week"], str):
            row["week"] = datetime.fromisoformat(row["week"]).date()
    return rows


def _build_training_matrix(rows: list[dict]) -> tuple[list[list[float]], list[float]]:
    features: list[list[float]] = []
    targets: list[float] = []
    prices = [float(row["avg_price"]) for row in rows]

    for idx in range(4, len(rows)):
        current_date = rows[idx]["week"]
        lag_slice = prices[max(0, idx - 4):idx]
        lag_std = pstdev(lag_slice) if len(lag_slice) > 1 else 0.0
        week_sin, week_cos = _week_of_year_factor(current_date)
        features.append(
            [
                float(idx),
                week_sin,
                week_cos,
                prices[idx - 1],
                prices[idx - 2],
                mean(lag_slice),
                lag_std,
                float(rows[idx - 1]["avg_buy_price"]),
                float(rows[idx - 1]["dollar"]),
                float(rows[idx - 1]["brent"]),
                float(rows[idx - 1]["ipca"]),
            ]
        )
        targets.append(prices[idx])
    return features, targets


def _forecast_random_forest(rows: list[dict], horizon_weeks: int) -> list[float]:
    features, targets = _build_training_matrix(rows)
    prices = [float(row["avg_price"]) for row in rows]

    if len(features) < 4:
        return [prices[-1]] * horizon_weeks

    model = RandomForestRegressor(
        n_estimators=320,
        max_depth=8,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(features, targets)

    last = rows[-1]
    current_date = last["week"]
    simulated_prices = prices[:]
    predictions: list[float] = []

    for step in range(1, horizon_weeks + 1):
        target_date = current_date + timedelta(weeks=step)
        lag_slice = simulated_prices[-4:]
        lag_std = pstdev(lag_slice) if len(lag_slice) > 1 else 0.0
        week_sin, week_cos = _week_of_year_factor(target_date)
        vector = [
            float(len(simulated_prices)),
            week_sin,
            week_cos,
            simulated_prices[-1],
            simulated_prices[-2] if len(simulated_prices) > 1 else simulated_prices[-1],
            mean(lag_slice),
            lag_std,
            float(last["avg_buy_price"]),
            float(last["dollar"]),
            float(last["brent"]),
            float(last["ipca"]),
        ]
        prediction = float(model.predict([vector])[0])
        simulated_prices.append(prediction)
        predictions.append(prediction)
    return predictions


def _forecast_exponential_smoothing(rows: list[dict], horizon_weeks: int) -> list[float]:
    prices = [float(row["avg_price"]) for row in rows]
    if len(prices) < 6:
        return [prices[-1]] * horizon_weeks

    model = ExponentialSmoothing(
        prices,
        trend="add",
        seasonal=None,
        damped_trend=True,
        initialization_method="estimated",
    ).fit(optimized=True)
    return [float(value) for value in model.forecast(horizon_weeks)]


def _interpolate_daily(
    anchor_dates: list[date],
    anchor_values: list[float],
    start_date: date,
    horizon_days: int,
) -> list[tuple[date, float]]:
    daily_points: list[tuple[date, float]] = []
    start_offset = max((start_date - anchor_dates[0]).days, 1)
    for offset in range(horizon_days):
        day = start_offset + offset
        target_date = start_date + timedelta(days=offset)
        upper_index = min(ceil(day / 7), len(anchor_values) - 1)
        lower_index = max(upper_index - 1, 0)
        lower_date = anchor_dates[lower_index]
        upper_date = anchor_dates[upper_index]
        lower_value = anchor_values[lower_index]
        upper_value = anchor_values[upper_index]
        span_days = max((upper_date - lower_date).days, 1)
        ratio = min(max((target_date - lower_date).days / span_days, 0.0), 1.0)
        interpolated = lower_value + (upper_value - lower_value) * ratio
        daily_points.append((target_date, interpolated))
    return daily_points


def forecast_series(series: pl.DataFrame, horizon: int = 15) -> list[dict]:
    if len(series) < 8:
        return []

    rows = _series_rows(series)
    last = rows[-1]
    last_avg = float(last["avg_price"])
    recent_prices = [float(row["avg_price"]) for row in rows[-8:]]
    recent_std = pstdev(recent_prices) if len(recent_prices) > 1 else 0.06
    horizon_weeks = max(3, ceil(horizon / 7) + 1)

    smoothing_predictions = _forecast_exponential_smoothing(rows, horizon_weeks)
    forest_predictions = _forecast_random_forest(rows, horizon_weeks)
    weekly_path = [
        (smoothing * 0.55) + (forest * 0.45)
        for smoothing, forest in zip(smoothing_predictions, forest_predictions, strict=False)
    ]

    anchor_dates = [last["week"]] + [last["week"] + timedelta(weeks=step) for step in range(1, horizon_weeks + 1)]
    anchor_values = [last_avg] + weekly_path
    forecast_start = max(last["week"] + timedelta(days=1), date.today() + timedelta(days=1))
    future_daily = _interpolate_daily(anchor_dates, anchor_values, forecast_start, horizon)

    points: list[dict] = []
    for offset, (target_date, expected) in enumerate(future_daily, start=1):
        spread = max(0.05, recent_std * 0.9, expected * 0.012)
        trend_gain = max(expected - last_avg, 0.0)
        trend_loss = max(last_avg - expected, 0.0)
        points.extend(
            [
                asdict(
                    ForecastPoint(
                        week=target_date.isoformat(),
                        predicted=round(expected - (spread * 0.25) - (trend_loss * 0.05), 3),
                        minimum=round(expected - spread * 0.9, 3),
                        maximum=round(expected + spread * 0.35, 3),
                        scenario="conservador",
                    )
                ),
                asdict(
                    ForecastPoint(
                        week=target_date.isoformat(),
                        predicted=round(expected, 3),
                        minimum=round(expected - spread * 0.7, 3),
                        maximum=round(expected + spread * 0.7, 3),
                        scenario="realista",
                    )
                ),
                asdict(
                    ForecastPoint(
                        week=target_date.isoformat(),
                        predicted=round(expected + (spread * 0.28) + (trend_gain * 0.06), 3),
                        minimum=round(expected - spread * 0.45, 3),
                        maximum=round(expected + spread * 0.95, 3),
                        scenario="agressivo",
                    )
                ),
            ]
        )
    return points
