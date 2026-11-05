"""Unit tests for forecasting evaluation metrics (pure Python / pytest)."""

import math
import numpy as np
import pytest

from forecasting.metrics import bias, rmsse, wape


def test_wape_perfect_forecast():
    """A perfect forecast must result in WAPE equal to 0.0."""
    actual = np.array([10.0, 20.0, 30.0, 40.0])
    forecast = np.array([10.0, 20.0, 30.0, 40.0])
    assert wape(actual, forecast) == 0.0


def test_bias_perfect_forecast():
    """A perfect forecast must result in Bias equal to 0.0."""
    actual = np.array([10.0, 20.0, 30.0, 40.0])
    forecast = np.array([10.0, 20.0, 30.0, 40.0])
    assert bias(actual, forecast) == 0.0


def test_rmsse_perfect_forecast():
    """A perfect forecast must result in RMSSE equal to 0.0."""
    train = np.array([5.0, 10.0, 15.0, 20.0])
    actual = np.array([25.0, 30.0])
    forecast = np.array([25.0, 30.0])
    assert rmsse(train, actual, forecast) == 0.0


def test_known_small_example_values():
    """Verify exact values against a hand-computed example.

    Train: [10, 12, 14, 16] -> diffs = [2, 2, 2], diffs^2 = [4, 4, 4], mean = 4.0
    Actual: [18, 20]
    Forecast: [19, 18]

    Errors:
        a - f = [-1, 2]
        |a - f| = [1, 2], sum = 3
        f - a = [1, -2], sum = -1
        sum(a) = 38
        (a - f)^2 = [1, 4], mean = 2.5

    Metrics:
        WAPE = 3 / 38 ≈ 0.078947368
        Bias = -1 / 38 ≈ -0.026315789
        RMSSE = sqrt(2.5 / 4.0) = sqrt(0.625) ≈ 0.790569415
    """
    train = [10.0, 12.0, 14.0, 16.0]
    actual = [18.0, 20.0]
    forecast = [19.0, 18.0]

    computed_wape = wape(actual, forecast)
    computed_bias = bias(actual, forecast)
    computed_rmsse = rmsse(train, actual, forecast)

    expected_wape = 3.0 / 38.0
    expected_bias = -1.0 / 38.0
    expected_rmsse = math.sqrt(2.5 / 4.0)

    assert pytest.approx(computed_wape, rel=1e-5) == expected_wape
    assert pytest.approx(computed_bias, rel=1e-5) == expected_bias
    assert pytest.approx(computed_rmsse, rel=1e-5) == expected_rmsse


def test_shape_mismatch_raises_error():
    """Mismatched shapes between actual and forecast must raise ValueError."""
    with pytest.raises(ValueError, match="Shape mismatch"):
        wape([1, 2], [1, 2, 3])

    with pytest.raises(ValueError, match="Shape mismatch"):
        bias([1, 2], [1])

    with pytest.raises(ValueError, match="Shape mismatch"):
        rmsse([1, 2, 3], [1, 2], [1])

