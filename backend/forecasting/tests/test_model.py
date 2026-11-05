"""Unit tests for LightGBM model training and prediction (pure Python / pytest)."""

import numpy as np
import pandas as pd
import pytest

from forecasting.model import get_feature_importance, predict, train_lgbm


@pytest.fixture
def synthetic_data():
    """Create small synthetic train and validation feature sets."""
    np.random.seed(42)
    n_train = 200
    n_valid = 50

    def make_df(n):
        return pd.DataFrame(
            {
                "store": np.random.choice(["S1", "S2"], size=n),
                "sku": np.random.choice(["P1", "P2"], size=n),
                "date": pd.date_range("2023-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
                "day_of_week": np.random.randint(0, 7, size=n),
                "price": np.random.uniform(1.0, 5.0, size=n),
                "on_promo": np.random.choice([0, 1], size=n),
                "lag_28": np.random.uniform(10.0, 100.0, size=n),
                "units_sold": np.random.uniform(10.0, 100.0, size=n),
            }
        )

    return make_df(n_train), make_df(n_valid)


def test_train_lgbm_and_predict(synthetic_data):
    """Train LightGBM model and verify predictions are clipped at 0."""
    train_df, valid_df = synthetic_data
    feature_cols = ["store", "sku", "day_of_week", "price", "on_promo", "lag_28"]

    model = train_lgbm(
        train_feat=train_df,
        valid_feat=valid_df,
        feature_cols=feature_cols,
        n_estimators=50,
        early_stopping_rounds=10,
    )

    preds = predict(model, valid_df, feature_cols)
    assert isinstance(preds, pd.DataFrame)
    assert list(preds.columns) == ["store", "sku", "date", "forecast"]
    assert len(preds) == len(valid_df)
    assert (preds["forecast"] >= 0).all()


def test_get_feature_importance(synthetic_data):
    """Feature importance DataFrame must be sorted descending."""
    train_df, valid_df = synthetic_data
    feature_cols = ["store", "sku", "day_of_week", "price", "on_promo", "lag_28"]

    model = train_lgbm(
        train_feat=train_df,
        valid_feat=valid_df,
        feature_cols=feature_cols,
        n_estimators=30,
        early_stopping_rounds=10,
    )

    imp = get_feature_importance(model, feature_cols)
    assert list(imp.columns) == ["feature", "importance"]
    assert len(imp) == len(feature_cols)
    # Check descending order
    assert imp["importance"].is_monotonic_decreasing

