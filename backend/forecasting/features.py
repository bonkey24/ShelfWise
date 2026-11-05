"""Feature engineering pipeline for retail demand forecasting.

Strictly time-ordered and leak-free feature construction.

Leakage Avoidance Strategy:
---------------------------
The validation window is 28 days ahead. To prevent lookahead data leakage:
1. For short-horizon/1-step models, rolling features use `shift(1)` so that
   the current day's actual sales never enters the rolling window.
2. For multi-step 28-day horizon models (Direct Forecasting), all lags must be
   >= 28 days (lags 28, 35, 42, 49, 56) and all rolling statistics must be shifted
   by 28 days (`shift(28)`). Because any validation observation at day `t` is at most
   28 days from the train cutoff `T`, `t - 28 <= T`. Therefore, every feature for
   every row in the validation window relies strictly on observations from the training
   period, guaranteeing zero leakage of valid-period actuals.
"""

import pandas as pd

# Standard 28-day horizon direct feature columns (guaranteed zero leakage for 28-day horizon)
DIRECT_28_FEATURE_COLS = [
    "store",
    "sku",
    "day_of_week",
    "month",
    "week_of_year",
    "day_of_month",
    "is_weekend",
    "price",
    "on_promo",
    "price_change",
    "lag_28",
    "lag_35",
    "lag_42",
    "lag_49",
    "lag_56",
    "rolling_mean_7_lag28",
    "rolling_std_7_lag28",
    "rolling_mean_28_lag28",
    "rolling_std_28_lag28",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Construct tabular ML features from sales time-series data.

    Why shift prevents data leakage:
    --------------------------------
    When predicting retail demand for day `t`, the actual sales value `units_sold`
    for day `t` is unknown and represents the target variable. If a rolling window
    is computed directly on `units_sold`, the rolling calculation at index `t`
    includes the value at index `t`: window = [y_{t-w+1}, ..., y_t].

    By shifting `units_sold` (by 1 for 1-step features, and by 28 for 28-day horizon
    forecasting), the rolling window ending at index `t` covers only past historical
    observations. For a 28-day validation window, using lags >= 28 and rolling
    aggregations shifted by 28 guarantees that validation rows never access
    validation-period actuals.

    Args:
        df: Input DataFrame containing columns:
            [store, sku, date, units_sold, price, on_promo]

    Returns:
        pd.DataFrame: Feature-enriched DataFrame sorted by store, sku, date.
    """
    required_cols = {"store", "sku", "date", "units_sold", "price", "on_promo"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for feature engineering: {missing}")

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)

    # Calendar features (known in advance for all dates)
    data["day_of_week"] = data["date"].dt.day_of_week
    data["month"] = data["date"].dt.month
    data["week_of_year"] = data["date"].dt.isocalendar().week.astype(int)
    data["day_of_month"] = data["date"].dt.day
    data["is_weekend"] = data["day_of_week"].isin([5, 6]).astype(int)

    # Grouped operations per (store, sku)
    grouped = data.groupby(["store", "sku"], group_keys=False, observed=False)

    # 1. Standard lags
    data["lag_7"] = grouped["units_sold"].shift(7)
    data["lag_14"] = grouped["units_sold"].shift(14)
    data["lag_28"] = grouped["units_sold"].shift(28)
    data["lag_35"] = grouped["units_sold"].shift(35)
    data["lag_42"] = grouped["units_sold"].shift(42)
    data["lag_49"] = grouped["units_sold"].shift(49)
    data["lag_56"] = grouped["units_sold"].shift(56)

    # 2. Rolling statistics shifted by 1 (for 1-step lookahead)
    data["rolling_mean_7"] = grouped["units_sold"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    )
    data["rolling_std_7"] = grouped["units_sold"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).std()
    )
    data["rolling_mean_28"] = grouped["units_sold"].transform(
        lambda s: s.shift(1).rolling(28, min_periods=1).mean()
    )
    data["rolling_std_28"] = grouped["units_sold"].transform(
        lambda s: s.shift(1).rolling(28, min_periods=1).std()
    )

    # 3. Rolling statistics shifted by 28 days (strictly leak-free for 28-day ahead direct forecasting)
    data["rolling_mean_7_lag28"] = grouped["units_sold"].transform(
        lambda s: s.shift(28).rolling(7, min_periods=1).mean()
    )
    data["rolling_std_7_lag28"] = grouped["units_sold"].transform(
        lambda s: s.shift(28).rolling(7, min_periods=1).std()
    )
    data["rolling_mean_28_lag28"] = grouped["units_sold"].transform(
        lambda s: s.shift(28).rolling(28, min_periods=1).mean()
    )
    data["rolling_std_28_lag28"] = grouped["units_sold"].transform(
        lambda s: s.shift(28).rolling(28, min_periods=1).std()
    )

    # 4. Price change vs previous day per (store, sku)
    data["price_change"] = grouped["price"].diff().fillna(0.0)

    # 5. Categorical encoding for entity IDs
    data["store"] = data["store"].astype("category")
    data["sku"] = data["sku"].astype("category")

    return data
