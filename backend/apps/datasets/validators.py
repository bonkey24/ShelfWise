"""Pandera validation schema and helper functions for sales dataset CSV uploads."""

from typing import Any
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors


# Pandera DataFrame schema definition
sales_schema = pa.DataFrameSchema(
    columns={
        "store": pa.Column(
            pa.String,
            nullable=False,
            coerce=True,
            description="Store identifier (e.g. S1)",
        ),
        "sku": pa.Column(
            pa.String,
            nullable=False,
            coerce=True,
            description="Product SKU identifier (e.g. P1)",
        ),
        "date": pa.Column(
            pa.DateTime,
            nullable=False,
            coerce=True,
            description="Transaction date (must be parseable into date/time)",
        ),
        "units_sold": pa.Column(
            pa.Float,
            pa.Check.greater_than_or_equal_to(0),
            nullable=False,
            coerce=True,
            description="Quantity of units sold (>= 0)",
        ),
        "price": pa.Column(
            pa.Float,
            pa.Check.greater_than_or_equal_to(0),
            nullable=True,
            coerce=True,
            description="Unit price (>= 0 or null)",
        ),
        "on_promo": pa.Column(
            pa.Int,
            pa.Check.isin([0, 1]),
            nullable=False,
            coerce=True,
            description="Promotion indicator (0 or 1)",
        ),
    },
    unique=["store", "sku", "date"],
    strict=False,
    coerce=True,
)


def format_pandera_errors(errors: SchemaErrors) -> list[str]:
    """Format Pandera SchemaErrors into readable, de-duplicated error messages.

    Includes column name, failure reason, and a few sample row numbers.
    """
    cases = errors.failure_cases
    if cases is None or cases.empty:
        return ["Data validation failed with unspecified schema errors."]

    formatted_errors: list[str] = []
    seen: set[str] = set()

    # Collect row indices and failure cases
    for (col, check), group in cases.groupby(["column", "check"], dropna=False):
        row_indices = [
            int(idx) + 1  # 1-based row index for humans (matches Excel / line view)
            for idx in group["index"].dropna().unique()[:5]
            if isinstance(idx, (int, float))
        ]
        sample_values = [
            str(v)
            for v in group["failure_case"].dropna().unique()[:3]
        ]
        rows_str = f" at row(s) {row_indices}" if row_indices else ""

        if check == "column_in_dataframe":
            missing_col = group["failure_case"].iloc[0]
            msg = f"Missing required column: '{missing_col}'"
        elif "uniqueness" in str(check).lower():
            msg = f"Duplicate (store, sku, date) combinations detected{rows_str}."
        elif "greater_than_or_equal_to(0)" in str(check):
            msg = f"Column '{col}': values must be >= 0, found invalid value(s) {sample_values}{rows_str}."
        elif "isin" in str(check).lower():
            msg = f"Column '{col}': values must be in [0, 1], found invalid value(s) {sample_values}{rows_str}."
        elif "coerce" in str(check).lower() or str(check) == "dtype":
            msg = f"Column '{col}': unable to parse required data type, invalid value(s) {sample_values}{rows_str}."
        else:
            msg = f"Column '{col}': validation check '{check}' failed for value(s) {sample_values}{rows_str}."

        if msg not in seen:
            seen.add(msg)
            formatted_errors.append(msg)

    return formatted_errors


def validate_sales_dataframe(df: pd.DataFrame) -> tuple[bool, pd.DataFrame, list[str]]:
    """Validate a sales DataFrame against the schema.

    Returns:
        (is_valid, validated_df, list_of_error_strings)
    """
    if df.empty:
        return False, df, ["Uploaded CSV is empty."]

    # Check for required columns first
    required_columns = {"store", "sku", "date", "units_sold", "price", "on_promo"}
    missing = required_columns - set(df.columns)
    if missing:
        return False, df, [f"Missing required column(s): {', '.join(sorted(missing))}"]

    try:
        validated_df = sales_schema.validate(df, lazy=True)
        return True, validated_df, []
    except SchemaErrors as err:
        errors = format_pandera_errors(err)
        return False, df, errors
