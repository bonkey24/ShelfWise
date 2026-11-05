"""Unit tests for time-based train/validation splitting (pure Python / pytest)."""

import pandas as pd
import pytest

from forecasting.split import three_way_split, time_split


@pytest.fixture
def sample_timeseries_df():
    """Create a multi-store, multi-sku dataset spanning 40 distinct dates."""
    dates = pd.date_range("2023-01-01", periods=40, freq="D")
    records = []
    for d in dates:
        for s in ["S1", "S2"]:
            for p in ["P1", "P2"]:
                records.append(
                    {
                        "store": s,
                        "sku": p,
                        "date": d.strftime("%Y-%m-%d"),
                        "units_sold": 10.0,
                    }
                )
    return pd.DataFrame(records)


def test_time_split_temporal_ordering(sample_timeseries_df):
    """Ensure max(train.date) < min(valid.date) and never overlaps."""
    valid_days = 10
    train, valid = time_split(sample_timeseries_df, valid_days=valid_days)

    assert not train.empty
    assert not valid.empty

    max_train_date = train["date"].max()
    min_valid_date = valid["date"].min()

    assert max_train_date < min_valid_date
    assert valid["date"].nunique() == valid_days
    assert train["date"].nunique() == 40 - valid_days


def test_time_split_is_never_random(sample_timeseries_df):
    """Multiple invocations must produce identical, strictly deterministic splits."""
    train1, valid1 = time_split(sample_timeseries_df, valid_days=14)
    train2, valid2 = time_split(sample_timeseries_df, valid_days=14)

    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(valid1, valid2)


def test_time_split_insufficient_dates():
    """Raise ValueError when unique dates in DataFrame <= valid_days."""
    df_short = pd.DataFrame(
        {
            "date": ["2023-01-01", "2023-01-02"],
            "units_sold": [5.0, 10.0],
        }
    )
    with pytest.raises(ValueError, match="not enough for a validation split"):
        time_split(df_short, valid_days=28)


def test_time_split_invalid_days():
    """Raise ValueError when valid_days <= 0."""
    df = pd.DataFrame({"date": ["2023-01-01"], "units_sold": [10.0]})
    with pytest.raises(ValueError, match="positive integer"):
        time_split(df, valid_days=0)


# ---- three_way_split tests ----


@pytest.fixture
def large_timeseries_df():
    """Create a multi-store dataset spanning 90 distinct dates."""
    dates = pd.date_range("2023-01-01", periods=90, freq="D")
    records = []
    for d in dates:
        for s in ["S1", "S2"]:
            records.append(
                {
                    "store": s,
                    "sku": "P1",
                    "date": d.strftime("%Y-%m-%d"),
                    "units_sold": 10.0,
                }
            )
    return pd.DataFrame(records)


def test_three_way_split_date_counts(large_timeseries_df):
    """Train/valid/test must have the correct number of unique dates."""
    train, valid, test = three_way_split(large_timeseries_df, valid_days=10, test_days=10)

    assert test["date"].nunique() == 10
    assert valid["date"].nunique() == 10
    assert train["date"].nunique() == 90 - 10 - 10


def test_three_way_split_no_overlap(large_timeseries_df):
    """The three splits must be non-overlapping and temporally ordered."""
    train, valid, test = three_way_split(large_timeseries_df, valid_days=14, test_days=14)

    assert train["date"].max() < valid["date"].min()
    assert valid["date"].max() < test["date"].min()


def test_three_way_split_insufficient_dates():
    """Raise ValueError when not enough unique dates for train+valid+test."""
    df_short = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=10, freq="D"),
            "units_sold": range(10),
        }
    )
    with pytest.raises(ValueError, match="need at least"):
        three_way_split(df_short, valid_days=5, test_days=5)


def test_three_way_split_deterministic(large_timeseries_df):
    """Three-way split must be deterministic across invocations."""
    t1, v1, te1 = three_way_split(large_timeseries_df, valid_days=14, test_days=14)
    t2, v2, te2 = three_way_split(large_timeseries_df, valid_days=14, test_days=14)

    pd.testing.assert_frame_equal(t1, t2)
    pd.testing.assert_frame_equal(v1, v2)
    pd.testing.assert_frame_equal(te1, te2)
