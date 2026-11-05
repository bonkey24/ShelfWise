"""Time-based dataset splitting for time series forecasting."""

import pandas as pd


def time_split(
    df: pd.DataFrame,
    valid_days: int = 28,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split DataFrame into train and validation sets based on unique dates.

    Sorts the data temporally. The last `valid_days` distinct dates are assigned
    to the validation set; all earlier dates form the training set. This split is
    strictly deterministic (never random) to prevent future data leakage.

    Args:
        df: Input DataFrame containing time series observations.
        valid_days: Number of recent unique dates to reserve for validation.
        date_col: Column name containing observation dates.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (train_df, valid_df)

    Raises:
        ValueError: If valid_days is not positive or if the DataFrame contains
            insufficient unique dates.
    """
    if valid_days <= 0:
        raise ValueError(f"valid_days must be a positive integer, got {valid_days}")

    if df.empty:
        raise ValueError("Cannot split an empty DataFrame")

    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame")

    # Sort DataFrame by date
    sorted_df = df.sort_values(by=date_col).copy()

    # Extract sorted unique dates
    unique_dates = sorted_df[date_col].drop_duplicates().tolist()

    if len(unique_dates) <= valid_days:
        raise ValueError(
            f"DataFrame contains {len(unique_dates)} unique dates, which is "
            f"not enough for a validation split of {valid_days} days."
        )

    cutoff_date = unique_dates[-valid_days]

    train_df = sorted_df[sorted_df[date_col] < cutoff_date].copy().reset_index(drop=True)
    valid_df = sorted_df[sorted_df[date_col] >= cutoff_date].copy().reset_index(drop=True)

    return train_df, valid_df


def three_way_split(
    df: pd.DataFrame,
    valid_days: int = 28,
    test_days: int = 28,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split DataFrame into train, validation, and test sets based on unique dates.

    The last `test_days` distinct dates form the test set (used only for final
    metric reporting). The preceding `valid_days` distinct dates form the
    validation set (used only for early stopping / hyper-parameter tuning). All
    earlier dates form the training set.

    This split is strictly deterministic and time-ordered to prevent data leakage.

    Args:
        df: Input DataFrame containing time series observations.
        valid_days: Number of dates to reserve for validation (early stopping).
        test_days: Number of dates to reserve for testing (final reporting).
        date_col: Column name containing observation dates.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            (train_df, valid_df, test_df)

    Raises:
        ValueError: If split parameters are invalid or the DataFrame has
            insufficient unique dates.
    """
    if valid_days <= 0:
        raise ValueError(f"valid_days must be a positive integer, got {valid_days}")
    if test_days <= 0:
        raise ValueError(f"test_days must be a positive integer, got {test_days}")

    if df.empty:
        raise ValueError("Cannot split an empty DataFrame")

    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame")

    sorted_df = df.sort_values(by=date_col).copy()
    unique_dates = sorted_df[date_col].drop_duplicates().tolist()

    needed = valid_days + test_days + 1  # at least 1 train day
    if len(unique_dates) < needed:
        raise ValueError(
            f"DataFrame contains {len(unique_dates)} unique dates, need at least "
            f"{needed} for train + {valid_days} valid + {test_days} test."
        )

    test_cutoff = unique_dates[-test_days]
    valid_cutoff = unique_dates[-(valid_days + test_days)]

    train_df = sorted_df[sorted_df[date_col] < valid_cutoff].copy().reset_index(drop=True)
    valid_df = sorted_df[
        (sorted_df[date_col] >= valid_cutoff) & (sorted_df[date_col] < test_cutoff)
    ].copy().reset_index(drop=True)
    test_df = sorted_df[sorted_df[date_col] >= test_cutoff].copy().reset_index(drop=True)

    return train_df, valid_df, test_df
