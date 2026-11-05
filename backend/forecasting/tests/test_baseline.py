"""Unit tests for baseline forecasting models (pure Python / pytest)."""

import pandas as pd
import pytest

from forecasting.baseline import (
    naive_forecast,
    seasonal_naive_28_forecast,
    seasonal_naive_forecast,
)
from forecasting.metrics import wape


@pytest.fixture
def history_df():
    """Create a 14-day history for (S1, P1)."""
    dates = pd.date_range("2023-01-01", periods=14, freq="D")
    # Day-of-week pattern: 100, 101, ..., 106, then 200, 201, ..., 206
    values = [100 + (i % 7) for i in range(7)] + [200 + (i % 7) for i in range(7)]
    return pd.DataFrame(
        {
            "store": ["S1"] * 14,
            "sku": ["P1"] * 14,
            "date": dates.strftime("%Y-%m-%d"),
            "units_sold": values,
        }
    )


def test_naive_forecast_repeats_last_value(history_df):
    """Naive baseline must repeat the final historical value across the horizon."""
    last_value = history_df["units_sold"].iloc[-1]  # 206
    horizon_df = pd.DataFrame(
        {
            "store": ["S1"] * 5,
            "sku": ["P1"] * 5,
            "date": pd.date_range("2023-01-15", periods=5, freq="D").strftime("%Y-%m-%d"),
        }
    )

    fc = naive_forecast(history_df, horizon=horizon_df)
    assert len(fc) == 5
    assert (fc["forecast"] == last_value).all()


def test_seasonal_naive_date_based_weekday_lookup(history_df):
    """Seasonal naive must use the latest train date with the same weekday."""
    # history_df: 2023-01-01 (Sun) to 2023-01-14 (Sat)
    # Week 2 values: Sun=200, Mon=201, Tue=202, Wed=203, Thu=204, Fri=205, Sat=206
    # Horizon: 2023-01-15 (Sun) to 2023-01-28 (Sat) x2
    horizon_df = pd.DataFrame(
        {
            "store": ["S1"] * 14,
            "sku": ["P1"] * 14,
            "date": pd.date_range("2023-01-15", periods=14, freq="D").strftime("%Y-%m-%d"),
        }
    )

    fc = seasonal_naive_forecast(history_df, horizon=horizon_df)
    assert len(fc) == 14

    # Each forecast date matches the latest same-weekday from history (week 2 values)
    expected_pattern = [200 + (i % 7) for i in range(7)] * 2
    assert fc["forecast"].tolist() == expected_pattern


def test_seasonal_naive_perfect_weekly_pattern():
    """Seasonal naive must yield WAPE=0 on a perfectly repeating weekly pattern.

    A series where every Monday is 100, every Tuesday is 200, etc.
    If the test dates repeat the exact same weekly pattern, seasonal naive
    (using the latest same-weekday value from training) should predict exactly.
    """
    # 8 full weeks of training (56 days) + 4 weeks test (28 days)
    # Pattern: value = (weekday + 1) * 100  -> Mon=100, Tue=200, ..., Sun=700
    all_dates = pd.date_range("2023-01-02", periods=84, freq="D")  # starts Monday
    values = [(d.day_of_week + 1) * 100 for d in all_dates]

    full_df = pd.DataFrame(
        {
            "store": ["S1"] * 84,
            "sku": ["P1"] * 84,
            "date": all_dates.strftime("%Y-%m-%d"),
            "units_sold": values,
        }
    )

    train_df = full_df.iloc[:56].copy()
    test_df = full_df.iloc[56:].copy()

    fc = seasonal_naive_forecast(train_df, horizon=test_df)
    assert len(fc) == 28

    # Because the pattern is perfectly weekly and constant, forecast should be exact
    test_actual = test_df["units_sold"].to_numpy()
    fc_values = fc["forecast"].to_numpy()

    assert wape(test_actual, fc_values) == 0.0


def test_seasonal_naive_uses_latest_not_positional():
    """Verify the forecast uses the *latest* matching weekday, not a fixed tail position.

    If the last 7 days have a different pattern than the previous weeks,
    the seasonal naive should use those latest values, not older ones.
    """
    # 21 days: weeks 1-2 have value 10 on Mondays, week 3 has value 999 on Monday
    dates = pd.date_range("2023-01-02", periods=21, freq="D")  # starts Monday
    values = []
    for d in dates:
        if d.day_of_week == 0:  # Monday
            values.append(999 if d >= pd.Timestamp("2023-01-16") else 10)
        else:
            values.append(50)

    history = pd.DataFrame(
        {
            "store": ["S1"] * 21,
            "sku": ["P1"] * 21,
            "date": dates.strftime("%Y-%m-%d"),
            "units_sold": values,
        }
    )

    # Forecast for next Monday (2023-01-23)
    horizon_df = pd.DataFrame(
        {
            "store": ["S1"],
            "sku": ["P1"],
            "date": ["2023-01-23"],
        }
    )

    fc = seasonal_naive_forecast(history, horizon=horizon_df)
    # Must use the latest Monday value (999), not older Monday value (10)
    assert fc["forecast"].iloc[0] == 999


def test_seasonal_naive_28_perfect_pattern():
    """Series repeating every 28 days must give WAPE=0 for seasonal_naive_28_forecast."""
    # 56 days of history (2 cycles of 28 days) + 28 days of horizon (1 cycle of 28 days)
    dates = pd.date_range("2023-01-01", periods=84, freq="D")
    # Arbitrary 28-day pattern
    pattern_28 = [(i * 3 + (i % 7) * 10 + 50) for i in range(28)]
    values = pattern_28 * 3  # exactly 3 repetitions

    df = pd.DataFrame(
        {
            "store": ["S1"] * 84,
            "sku": ["P1"] * 84,
            "date": dates.strftime("%Y-%m-%d"),
            "units_sold": values,
        }
    )

    history_df = df.iloc[:56].copy()
    horizon_df = df.iloc[56:].copy()

    fc = seasonal_naive_28_forecast(history_df, horizon=horizon_df)
    assert len(fc) == 28

    actuals = horizon_df["units_sold"].to_numpy()
    preds = fc["forecast"].to_numpy()

    assert wape(actuals, preds) == 0.0


def test_key_based_merge_immune_to_shuffling():
    """Verify that merging on (store, sku, date) yields identical metrics even when order is completely shuffled.

    Demonstrates that key-based alignment prevents catastrophic errors caused by positional alignment.
    """
    from forecasting.metrics import bias, wape

    # Two stores with distinct series levels (S1 ~ 100, S2 ~ 5000)
    dates_hist = pd.date_range("2023-01-01", periods=28, freq="D")
    dates_test = pd.date_range("2023-01-29", periods=14, freq="D")

    hist_rows = []
    for d in dates_hist:
        hist_rows.append({"store": "S1", "sku": "P1", "date": d.strftime("%Y-%m-%d"), "units_sold": 100.0 + d.day})
        hist_rows.append({"store": "S2", "sku": "P1", "date": d.strftime("%Y-%m-%d"), "units_sold": 5000.0 + d.day * 10})
    history_df = pd.DataFrame(hist_rows)

    test_rows = []
    for d in dates_test:
        test_rows.append({"store": "S1", "sku": "P1", "date": d.strftime("%Y-%m-%d"), "units_sold": 110.0 + d.day})
        test_rows.append({"store": "S2", "sku": "P1", "date": d.strftime("%Y-%m-%d"), "units_sold": 5200.0 + d.day * 10})
    test_actuals = pd.DataFrame(test_rows)
    test_actuals["store"] = test_actuals["store"].astype(str)
    test_actuals["sku"] = test_actuals["sku"].astype(str)
    test_actuals["date"] = pd.to_datetime(test_actuals["date"])

    fc = naive_forecast(history_df, horizon=test_actuals)

    # 1. Metric with original order
    merged_orig = pd.merge(test_actuals, fc, on=["store", "sku", "date"], how="inner")
    assert len(merged_orig) == len(test_actuals)
    wape_orig = wape(merged_orig["units_sold"], merged_orig["forecast"])
    bias_orig = bias(merged_orig["units_sold"], merged_orig["forecast"])

    # 2. Metric when baseline output is completely shuffled and actuals are in reverse order
    fc_shuffled = fc.sample(frac=1.0, random_state=42).reset_index(drop=True)
    test_shuffled = test_actuals.sample(frac=1.0, random_state=99).reset_index(drop=True)

    merged_shuffled = pd.merge(test_shuffled, fc_shuffled, on=["store", "sku", "date"], how="inner")
    assert len(merged_shuffled) == len(test_actuals)
    wape_shuffled = wape(merged_shuffled["units_sold"], merged_shuffled["forecast"])
    bias_shuffled = bias(merged_shuffled["units_sold"], merged_shuffled["forecast"])

    # Both must be bit-for-bit / float-identical
    assert pytest.approx(wape_orig) == wape_shuffled
    assert pytest.approx(bias_orig) == bias_shuffled


