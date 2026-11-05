"""Baseline forecasting models (Naive and Seasonal Naive) for retail demand."""

from typing import Any, Sequence
import pandas as pd


def _resolve_target_dataframe(
    history: pd.DataFrame,
    horizon: int | pd.DataFrame | Sequence[Any],
) -> pd.DataFrame:
    """Helper to construct target (store, sku, date) DataFrame for the forecast horizon."""
    if isinstance(horizon, pd.DataFrame):
        req_cols = {"store", "sku", "date"}
        if not req_cols.issubset(horizon.columns):
            raise ValueError(f"horizon DataFrame must contain {req_cols}")
        target = horizon[["store", "sku", "date"]].copy()
        target["store"] = target["store"].astype(str)
        target["sku"] = target["sku"].astype(str)
        target["date"] = pd.to_datetime(target["date"])
        return target

    # If horizon is an integer number of days
    if isinstance(horizon, int):
        if horizon <= 0:
            raise ValueError(f"horizon must be positive, got {horizon}")
        history_dates = pd.to_datetime(history["date"])
        max_date = history_dates.max()
        future_dates = pd.date_range(
            start=max_date + pd.Timedelta(days=1),
            periods=horizon,
            freq="D",
        )
        groups = history[["store", "sku"]].drop_duplicates()
        rows = []
        for _, g in groups.iterrows():
            for d in future_dates:
                rows.append({"store": g["store"], "sku": g["sku"], "date": d})
        return pd.DataFrame(rows)

    raise TypeError(f"Unsupported horizon type: {type(horizon)}")


def naive_forecast(
    history: pd.DataFrame,
    horizon: int | pd.DataFrame | Sequence[Any],
    target_col: str = "units_sold",
) -> pd.DataFrame:
    """Naive baseline forecast: repeats the last observed value per (store, sku).

    Args:
        history: Historical observations with store, sku, date, and target_col.
        horizon: Forecast horizon (int number of days or DataFrame of target dates).
        target_col: Column to forecast (defaults to 'units_sold').

    Returns:
        pd.DataFrame: DataFrame with columns [store, sku, date, forecast].
    """
    hist = history.copy()
    hist["store"] = hist["store"].astype(str)
    hist["sku"] = hist["sku"].astype(str)
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.sort_values(by=["store", "sku", "date"])

    # Get last known value per (store, sku)
    last_known = (
        hist.groupby(["store", "sku"], as_index=False, observed=False)
        .last()[["store", "sku", target_col]]
        .rename(columns={target_col: "forecast"})
    )

    target_df = _resolve_target_dataframe(history, horizon)
    merged = pd.merge(target_df, last_known, on=["store", "sku"], how="left")
    return merged.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)


def seasonal_naive_forecast(
    history: pd.DataFrame,
    horizon: int | pd.DataFrame | Sequence[Any],
    target_col: str = "units_sold",
) -> pd.DataFrame:
    """Seasonal Naive baseline: date-based weekday lookup from training history.

    For each forecast date d, finds the latest date in history for the same
    (store, sku) that falls on the same day-of-week as d, and uses its
    target_col value as the forecast. This is a proper date-based lookup —
    not a positional repeat — so it correctly captures weekly seasonality
    regardless of gaps or horizon length.

    Actual values from the evaluation horizon are never used.

    Args:
        history: Historical observations with store, sku, date, and target_col.
        horizon: Forecast horizon (int number of days or DataFrame of target dates).
        target_col: Column to forecast (defaults to 'units_sold').

    Returns:
        pd.DataFrame: DataFrame with columns [store, sku, date, forecast].
    """
    hist = history.copy()
    hist["store"] = hist["store"].astype(str)
    hist["sku"] = hist["sku"].astype(str)
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.sort_values(by=["store", "sku", "date"])
    hist["day_of_week"] = hist["date"].dt.day_of_week

    # For each (store, sku, day_of_week), keep the latest observed value
    latest_per_weekday = (
        hist.sort_values("date")
        .groupby(["store", "sku", "day_of_week"], as_index=False, observed=False)
        .last()[["store", "sku", "day_of_week", target_col]]
        .rename(columns={target_col: "forecast"})
    )

    target_df = _resolve_target_dataframe(history, horizon)
    target_df["day_of_week"] = target_df["date"].dt.day_of_week

    merged = pd.merge(
        target_df,
        latest_per_weekday,
        on=["store", "sku", "day_of_week"],
        how="left",
    )

    # Fallback: if a weekday was never observed, use naive last value
    if merged["forecast"].isna().any():
        fallback = (
            hist.groupby(["store", "sku"], as_index=False, observed=False)
            .last()[["store", "sku", target_col]]
            .rename(columns={target_col: "fallback_forecast"})
        )
        merged = pd.merge(merged, fallback, on=["store", "sku"], how="left")
        merged["forecast"] = merged["forecast"].fillna(merged["fallback_forecast"])
        merged = merged.drop(columns=["fallback_forecast"])

    result = merged.drop(columns=["day_of_week"])
    return result.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)


def seasonal_naive_28_forecast(
    history: pd.DataFrame,
    horizon: int | pd.DataFrame | Sequence[Any],
    target_col: str = "units_sold",
) -> pd.DataFrame:
    """Seasonal Naive 28-day baseline forecast: uses the value from exactly 28 days earlier.

    For each forecast date d and each (store, sku), looks up the actual units_sold
    from date (d - 28 days) in history. Because 28 is a multiple of 7, this preserves
    the day-of-week while aligning with multi-week cycles (such as 2-week promo patterns).

    Args:
        history: Historical observations with store, sku, date, and target_col.
        horizon: Forecast horizon (int number of days or DataFrame of target dates).
        target_col: Column to forecast (defaults to 'units_sold').

    Returns:
        pd.DataFrame: DataFrame with columns [store, sku, date, forecast].
    """
    hist = history.copy()
    hist["store"] = hist["store"].astype(str)
    hist["sku"] = hist["sku"].astype(str)
    hist["date"] = pd.to_datetime(hist["date"])
    target_df = _resolve_target_dataframe(history, horizon)
    target_df["lookup_date"] = target_df["date"] - pd.Timedelta(days=28)

    lookup_df = hist[["store", "sku", "date", target_col]].rename(
        columns={"date": "lookup_date", target_col: "forecast"}
    )

    merged = pd.merge(
        target_df,
        lookup_df,
        on=["store", "sku", "lookup_date"],
        how="left",
    )

    # Fallback: if d-28 was not in history, use naive last known value
    if merged["forecast"].isna().any():
        last_known = (
            hist.groupby(["store", "sku"], as_index=False, observed=False)
            .last()[["store", "sku", target_col]]
            .rename(columns={target_col: "fallback_forecast"})
        )
        merged = pd.merge(merged, last_known, on=["store", "sku"], how="left")
        merged["forecast"] = merged["forecast"].fillna(merged["fallback_forecast"])
        merged = merged.drop(columns=["fallback_forecast"])

    result = merged.drop(columns=["lookup_date"])
    return result.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)
