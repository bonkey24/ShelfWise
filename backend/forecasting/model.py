"""LightGBM demand forecasting model training, prediction, and feature importance.

Plain Python implementation (no Django imports).

Leakage Avoidance Strategy:
---------------------------
The evaluation horizon spans 28 days into the future. To completely avoid
using validation-period actuals:
- We employ direct multi-step forecasting with a 28-day lag horizon.
- All auto-regressive lags used by the model are >= 28 days (lags 28, 35, 42, 49, 56).
- All rolling statistics are pre-shifted by 28 days (`shift(28)`).
- Consequently, for any date `t` in the 28-day validation window, the newest observation
  accessed is at `t - 28 <= T_train`. This guarantees that zero ground-truth values
  from the validation window leak into the features.
"""

from typing import Sequence
import os
import warnings
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor, early_stopping, log_evaluation


def train_lgbm(
    train_feat: pd.DataFrame,
    valid_feat: pd.DataFrame,
    feature_cols: Sequence[str],
    target_col: str = "units_sold",
    categorical_cols: Sequence[str] = ("store", "sku"),
    n_estimators: int = 600,
    learning_rate: float = 0.05,
    num_leaves: int = 31,
    early_stopping_rounds: int = 50,
    random_state: int = 42,
    n_jobs: int | None = None,
) -> LGBMRegressor:
    """Train an LGBMRegressor with early stopping on the validation set.

    Drops rows containing NaN values in feature_cols or target_col before training.
    Configured with categorical features for store and sku, objective='regression',
    n_estimators=600, learning_rate=0.05, and num_leaves=31.

    Args:
        train_feat: Training feature DataFrame.
        valid_feat: Validation feature DataFrame.
        feature_cols: List of feature column names to train on.
        target_col: Name of the target column (defaults to 'units_sold').
        categorical_cols: Names of categorical feature columns.
        n_estimators: Maximum number of boosting trees (default: 600).
        learning_rate: Boosting learning rate (default: 0.05).
        num_leaves: Maximum tree leaves for base learners (default: 31).
        early_stopping_rounds: Number of rounds for early stopping on validation.
        random_state: Random seed for reproducibility.

    Returns:
        LGBMRegressor: Fitted LightGBM regressor model.
    """
    feature_cols = list(feature_cols)
    cols_to_check = feature_cols + [target_col]

    # Drop rows with NaN target or NaN lag features
    train_clean = train_feat.dropna(subset=cols_to_check).copy()
    valid_clean = valid_feat.dropna(subset=cols_to_check).copy()

    if train_clean.empty:
        raise ValueError("Training dataset has 0 rows after dropping NaN lag/target values.")
    if valid_clean.empty:
        raise ValueError("Validation dataset has 0 rows after dropping NaN lag/target values.")

    # Identify categorical features present in feature_cols
    cats = [c for c in categorical_cols if c in feature_cols]
    for c in cats:
        combined = pd.concat([train_clean[c], valid_clean[c]]).astype(str).unique()
        cat_type = pd.CategoricalDtype(categories=sorted(combined))
        train_clean[c] = train_clean[c].astype(cat_type)
        valid_clean[c] = valid_clean[c].astype(cat_type)

    X_train = train_clean[feature_cols]
    y_train = train_clean[target_col].to_numpy()

    X_valid = valid_clean[feature_cols]
    y_valid = valid_clean[target_col].to_numpy()

    model_params = {
        "objective": "regression",
        "n_estimators": n_estimators,
        "learning_rate": learning_rate,
        "num_leaves": num_leaves,
        "random_state": random_state,
        "verbose": -1,
    }
    thread_env = os.environ.get("LIGHTGBM_NUM_THREADS") or os.environ.get("LIGHTGBM_N_JOBS")
    if n_jobs is not None:
        model_params["n_jobs"] = n_jobs
    elif thread_env:
        try:
            model_params["n_jobs"] = int(thread_env)
        except ValueError:
            pass

    model = LGBMRegressor(**model_params)

    callbacks = [
        early_stopping(stopping_rounds=early_stopping_rounds, verbose=False),
        log_evaluation(period=0),
    ]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_valid, y_valid)],
            categorical_feature=cats if cats else "auto",
            callbacks=callbacks,
        )

    return model


def predict(
    model: LGBMRegressor,
    feat: pd.DataFrame,
    feature_cols: Sequence[str],
    categorical_cols: Sequence[str] = ("store", "sku"),
) -> pd.DataFrame:
    """Generate predictions from a fitted LightGBM model, clipped at zero.

    Args:
        model: Fitted LGBMRegressor model.
        feat: DataFrame containing input features and metadata columns (store, sku, date).
        feature_cols: List of feature column names.
        categorical_cols: Names of categorical feature columns to ensure category dtype.

    Returns:
        pd.DataFrame: DataFrame with columns [store, sku, date, forecast].
    """
    feature_cols = list(feature_cols)
    X = feat[feature_cols].copy()
    for c in categorical_cols:
        if c in X.columns:
            X[c] = X[c].astype("category")
    raw_preds = model.predict(X)
    clipped = np.clip(raw_preds, 0.0, None)

    res = pd.DataFrame(index=feat.index)
    res["store"] = feat["store"].astype(str) if "store" in feat.columns else "UNKNOWN"
    res["sku"] = feat["sku"].astype(str) if "sku" in feat.columns else "UNKNOWN"
    res["date"] = pd.to_datetime(feat["date"]) if "date" in feat.columns else pd.NaT
    res["forecast"] = clipped
    return res[["store", "sku", "date", "forecast"]].copy().reset_index(drop=True)


def get_feature_importance(
    model: LGBMRegressor,
    feature_cols: Sequence[str],
) -> pd.DataFrame:
    """Extract feature importances sorted in descending order.

    Args:
        model: Fitted LGBMRegressor model.
        feature_cols: Sequence of feature column names.

    Returns:
        pd.DataFrame: DataFrame with columns ['feature', 'importance'], sorted descending.
    """
    feature_cols = list(feature_cols)
    importances = model.feature_importances_
    df_imp = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": importances,
        }
    ).sort_values(by="importance", ascending=False).reset_index(drop=True)
    return df_imp
