"""Services for sales dataset ingestion and validation."""

import os
from typing import Optional, Tuple
from django.db import transaction
import pandas as pd

from apps.retail.models import Product, Sale, Store
from .models import Dataset
from .validators import validate_sales_dataframe


def ingest_sales_csv(
    file_path: str,
    dataset: Optional[Dataset] = None,
    dataset_name: Optional[str] = None,
) -> Tuple[Dataset, int]:
    """Parse, validate, and bulk-import sales CSV records into PostgreSQL.

    Args:
        file_path: Absolute or relative filesystem path to the sales CSV.
        dataset: Optional existing Dataset instance. If None, a new one is created.
        dataset_name: Name for the dataset if creating a new one.

    Returns:
        Tuple of (Dataset instance, count of rows imported).

    Raises:
        ValueError: If file parsing or Pandera schema validation fails.
        Exception: If database transaction or ingestion fails.
    """
    if dataset is None:
        name = dataset_name or os.path.basename(file_path)
        dataset = Dataset.objects.create(
            name=name,
            status="processing",
        )
    else:
        dataset.status = "processing"
        dataset.save(update_fields=["status"])

    try:
        df = pd.read_csv(file_path)
    except Exception as read_err:
        error_msg = f"Failed to parse CSV file: {read_err}"
        dataset.status = "failed"
        dataset.error = error_msg
        dataset.save(update_fields=["status", "error"])
        raise ValueError(error_msg)

    is_valid, validated_df, validation_errors = validate_sales_dataframe(df)
    if not is_valid:
        error_msg = "\n".join(validation_errors)
        dataset.status = "failed"
        dataset.error = error_msg
        dataset.save(update_fields=["status", "error"])
        raise ValueError(error_msg)

    try:
        with transaction.atomic():
            # 1. Bulk get or create Stores
            unique_stores = validated_df["store"].dropna().astype(str).unique()
            existing_stores = {
                s.code: s for s in Store.objects.filter(code__in=unique_stores)
            }
            new_stores = [
                Store(code=code)
                for code in unique_stores
                if code not in existing_stores
            ]
            if new_stores:
                Store.objects.bulk_create(new_stores, ignore_conflicts=True)
                existing_stores = {
                    s.code: s for s in Store.objects.filter(code__in=unique_stores)
                }

            # 2. Bulk get or create Products
            unique_skus = validated_df["sku"].dropna().astype(str).unique()
            existing_products = {
                p.sku: p for p in Product.objects.filter(sku__in=unique_skus)
            }
            new_products = [
                Product(sku=sku)
                for sku in unique_skus
                if sku not in existing_products
            ]
            if new_products:
                Product.objects.bulk_create(new_products, ignore_conflicts=True)
                existing_products = {
                    p.sku: p for p in Product.objects.filter(sku__in=unique_skus)
                }

            # 3. Bulk create Sale rows
            validated_df["parsed_date"] = pd.to_datetime(validated_df["date"]).dt.date
            sales_to_create = [
                Sale(
                    store=existing_stores[str(row.store)],
                    product=existing_products[str(row.sku)],
                    date=row.parsed_date,
                    units_sold=float(row.units_sold),
                    price=(
                        float(row.price)
                        if pd.notna(row.price) and row.price != ""
                        else None
                    ),
                    on_promo=bool(int(row.on_promo)),
                )
                for row in validated_df.itertuples(index=False)
            ]

            Sale.objects.bulk_create(
                sales_to_create,
                batch_size=5000,
                ignore_conflicts=True,
            )

        dataset.status = "done"
        dataset.rows_imported = len(sales_to_create)
        dataset.error = ""
        dataset.save(update_fields=["status", "rows_imported", "error"])
        return dataset, len(sales_to_create)

    except Exception as import_err:
        error_msg = f"Database import error: {import_err}"
        dataset.status = "failed"
        dataset.error = error_msg
        dataset.save(update_fields=["status", "error"])
        raise

