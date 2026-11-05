"""Unit tests for feature engineering and data leakage prevention (pure Python / pytest)."""

import numpy as np
import pandas as pd
import pytest

from forecasting.features import DIRECT_28_FEATURE_COLS, build_features
from forecasting.split import three_way_split, time_split


@pytest.fixture
def sales_series_df():
    """Create a 60-day time series for a single store and SKU."""
    dates = pd.date_range("2023-01-01", periods=60, freq="D")
    np.random.seed(42)
    return pd.DataFrame(
        {
            "store": ["S1"] * 60,
            "sku": ["P1"] * 60,
            "date": dates.strftime("%Y-%m-%d"),
            "units_sold": np.random.randint(10, 50, size=60).astype(float),
            "price": [2.99] * 60,
            "on_promo": [0] * 60,
        }
    )


def test_leakage_on_last_date(sales_series_df):
    """LEAKAGE TEST: Changing units_sold on the last date must NOT change its own features.

    Because lags (7, 14, 28) and rolling statistics (mean/std computed on shift(1))
    rely exclusively on prior historical observations, contaminating the target on
    day `t` must leave day `t` features completely unaltered.
    """
    df_original = sales_series_df.copy()
    df_mutated = sales_series_df.copy()

    # Change the last day's units_sold from normal value to a massive outlier
    df_mutated.iloc[-1, df_mutated.columns.get_loc("units_sold")] = 999_999_999.0

    features_orig = build_features(df_original)
    features_mut = build_features(df_mutated)

    # Feature columns that must not be contaminated
    leakage_sensitive_cols = [
        "lag_7",
        "lag_14",
        "lag_28",
        "rolling_mean_7",
        "rolling_std_7",
        "rolling_mean_28",
        "rolling_std_28",
        "price_change",
        "day_of_week",
        "month",
        "week_of_year",
        "day_of_month",
        "is_weekend",
    ]

    last_row_orig = features_orig.iloc[-1][leakage_sensitive_cols]
    last_row_mut = features_mut.iloc[-1][leakage_sensitive_cols]

    # Every feature for the last row must remain identical
    pd.testing.assert_series_equal(last_row_orig, last_row_mut)


def test_no_validation_period_leakage():
    """LEAKAGE TEST (28-day horizon): Validation-period actuals must not leak into validation features.

    When forecasting 28 days ahead, features for all rows in the 28-day validation window
    must rely strictly on training-period actuals. We verify that corrupting units_sold
    across the ENTIRE 28-day validation period results in exactly zero change to any feature
    in DIRECT_28_FEATURE_COLS for the validation window.
    """
    dates = pd.date_range("2023-01-01", periods=90, freq="D")
    np.random.seed(42)
    records = []
    for d in dates:
        for s in ["S1", "S2"]:
            for p in ["P1", "P2"]:
                records.append(
                    {
                        "store": s,
                        "sku": p,
                        "date": d.strftime("%Y-%m-%d"),
                        "units_sold": float(np.random.randint(10, 50)),
                        "price": 2.99,
                        "on_promo": int(np.random.choice([0, 1])),
                    }
                )
    df_clean = pd.DataFrame(records)

    # Find the 28-day validation cutoff date
    train_raw, valid_raw = time_split(df_clean, valid_days=28)
    cutoff_date = valid_raw["date"].min()

    # Create mutated DataFrame where validation actuals are replaced with extreme values
    df_corrupted = df_clean.copy()
    valid_mask = df_corrupted["date"] >= cutoff_date
    df_corrupted.loc[valid_mask, "units_sold"] = (
        df_corrupted.loc[valid_mask, "units_sold"] * 10_000.0 + 888_888.0
    )

    feat_clean = build_features(df_clean)
    feat_corrupted = build_features(df_corrupted)

    # Filter to validation rows
    valid_clean_feat = feat_clean[feat_clean["date"] >= cutoff_date].reset_index(drop=True)
    valid_corrupt_feat = feat_corrupted[feat_corrupted["date"] >= cutoff_date].reset_index(drop=True)

    # Every feature in DIRECT_28_FEATURE_COLS must remain strictly identical
    pd.testing.assert_frame_equal(
        valid_clean_feat[DIRECT_28_FEATURE_COLS],
        valid_corrupt_feat[DIRECT_28_FEATURE_COLS],
    )


def test_categorical_dtypes(sales_series_df):
    """store and sku must be converted to pandas 'category' dtype."""
    feat = build_features(sales_series_df)
    assert feat["store"].dtype.name == "category"
    assert feat["sku"].dtype.name == "category"


def test_calendar_features():
    """Verify calendar feature values on known fixed dates."""
    df = pd.DataFrame(
        {
            "store": ["S1", "S1"],
            "sku": ["P1", "P1"],
            "date": ["2023-01-01", "2023-01-02"],  # Sunday, Monday
            "units_sold": [10.0, 15.0],
            "price": [3.0, 3.5],
            "on_promo": [0, 1],
        }
    )
    feat = build_features(df)

    # 2023-01-01 is Sunday (day_of_week=6, is_weekend=1, month=1, day=1)
    row0 = feat.iloc[0]
    assert row0["day_of_week"] == 6
    assert row0["is_weekend"] == 1
    assert row0["month"] == 1
    assert row0["day_of_month"] == 1

    # 2023-01-02 is Monday (day_of_week=0, is_weekend=0, month=1, day=2)
    row1 = feat.iloc[1]
    assert row1["day_of_week"] == 0
    assert row1["is_weekend"] == 0
    assert row1["price_change"] == pytest.approx(0.5)
