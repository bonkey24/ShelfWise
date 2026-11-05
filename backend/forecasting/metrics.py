"""Forecasting evaluation metrics implemented using NumPy and Pandas only."""

from typing import Sequence
import numpy as np
import pandas as pd


def wape(
    actual: np.ndarray | pd.Series | Sequence[float],
    forecast: np.ndarray | pd.Series | Sequence[float],
) -> float:
    """Weighted Absolute Percentage Error (WAPE).

    Formula:
        WAPE = sum(|actual - forecast|) / sum(actual)

    Args:
        actual: Ground truth target values.
        forecast: Predicted values.

    Returns:
        float: Computed WAPE metric value.
    """
    a = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)

    if a.shape != f.shape:
        raise ValueError(f"Shape mismatch: actual shape {a.shape} vs forecast shape {f.shape}")

    sum_actual = np.sum(a)
    if sum_actual == 0:
        return 0.0 if np.all(a == f) else float("nan")

    return float(np.sum(np.abs(a - f)) / sum_actual)


def bias(
    actual: np.ndarray | pd.Series | Sequence[float],
    forecast: np.ndarray | pd.Series | Sequence[float],
) -> float:
    """Forecast Bias (normalized error).

    Positive values indicate over-forecasting; negative values indicate under-forecasting.

    Formula:
        Bias = sum(forecast - actual) / sum(actual)

    Args:
        actual: Ground truth target values.
        forecast: Predicted values.

    Returns:
        float: Computed Bias metric value.
    """
    a = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)

    if a.shape != f.shape:
        raise ValueError(f"Shape mismatch: actual shape {a.shape} vs forecast shape {f.shape}")

    sum_actual = np.sum(a)
    if sum_actual == 0:
        return 0.0 if np.all(a == f) else float("nan")

    return float(np.sum(f - a) / sum_actual)


def rmsse(
    train_actual: np.ndarray | pd.Series | Sequence[float],
    actual: np.ndarray | pd.Series | Sequence[float],
    forecast: np.ndarray | pd.Series | Sequence[float],
) -> float:
    """Root Mean Squared Scaled Error (RMSSE).

    Scales forecast MSE by in-sample one-step naive benchmark MSE.

    Formula:
        RMSSE = sqrt( mean((actual - forecast)^2) / mean(diff(train_actual)^2) )

    Args:
        train_actual: Historical in-sample target observations used for scaling.
        actual: Evaluation period ground truth target values.
        forecast: Evaluation period predicted values.

    Returns:
        float: Computed RMSSE metric value.
    """
    t_a = np.asarray(train_actual, dtype=float)
    a = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)

    if a.shape != f.shape:
        raise ValueError(f"Shape mismatch: actual shape {a.shape} vs forecast shape {f.shape}")

    if len(t_a) < 2:
        raise ValueError("train_actual must contain at least 2 observations to compute diff.")

    numerator = np.mean((a - f) ** 2)
    diffs = np.diff(t_a)
    denominator = np.mean(diffs ** 2)

    if denominator == 0:
        return 0.0 if numerator == 0 else float("inf")

    return float(np.sqrt(numerator / denominator))

