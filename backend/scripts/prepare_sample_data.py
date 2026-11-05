# SKUs and prices are simulated from Rossmann store-level sales.
"""Prepare sample sales data from raw Rossmann store sales data.

Reads data/raw/train.csv and data/raw/store.csv, filters to top 10 stores
and date range 2013-08-01 to 2015-07-31, simulates 5 products per store-day,
and writes data/sample_sales.csv.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# 5 simulated products with categories, baseline shares, and baseline prices
PRODUCTS = [
    {"sku": "P1", "category": "Dairy", "base_share": 0.30, "base_price": 2.99},
    {"sku": "P2", "category": "Bakery", "base_share": 0.25, "base_price": 1.99},
    {"sku": "P3", "category": "Beverages", "base_share": 0.20, "base_price": 1.49},
    {"sku": "P4", "category": "Snacks", "base_share": 0.15, "base_price": 2.49},
    {"sku": "P5", "category": "Household", "base_share": 0.10, "base_price": 4.99},
]


def prepare_sample_data(project_root: Path | None = None) -> pd.DataFrame:
    if project_root is None:
        # Resolve project root from this file location: backend/scripts -> project root
        project_root = Path(__file__).resolve().parents[2]

    train_csv_path = project_root / "data" / "raw" / "train.csv"
    store_csv_path = project_root / "data" / "raw" / "store.csv"
    output_csv_path = project_root / "data" / "sample_sales.csv"

    print(f"Reading {train_csv_path} and {store_csv_path}...")
    df_train = pd.read_csv(train_csv_path, low_memory=False)
    _df_store = pd.read_csv(store_csv_path)

    # 1. Keep only rows where Open == 1 and Sales > 0
    df = df_train[(df_train["Open"] == 1) & (df_train["Sales"] > 0)].copy()

    # 2. Keep the 10 stores with the most rows (store codes like "S1", "S2" from Store id)
    top_stores = df["Store"].value_counts().head(10).index
    df = df[df["Store"].isin(top_stores)].copy()

    # 3. Keep dates from 2013-08-01 to 2015-07-31
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[(df["Date"] >= "2013-08-01") & (df["Date"] <= "2015-07-31")].copy()

    df["store"] = "S" + df["Store"].astype(str)
    df["date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["on_promo"] = df["Promo"].astype(int)

    # 4. Simulate 5 products per store: P1..P5
    # Split each store-day's Sales into 5 units_sold values using fixed per-product shares
    # with small seeded random noise (np.random.seed(42)), rounded to whole numbers.
    np.random.seed(42)
    n_rows = len(df)
    base_shares = np.array([p["base_share"] for p in PRODUCTS])
    base_prices = np.array([p["base_price"] for p in PRODUCTS])

    # Share noise
    share_noise = np.random.normal(0, 0.01, size=(n_rows, len(PRODUCTS)))
    noisy_shares = base_shares + share_noise
    noisy_shares = np.clip(noisy_shares, 0.01, None)
    noisy_shares = noisy_shares / noisy_shares.sum(axis=1, keepdims=True)

    sales = df["Sales"].to_numpy()
    units_sold_matrix = np.round(sales[:, None] * noisy_shares).astype(int)

    # 5. Price: fixed base price per product plus small seeded noise; on_promo: Promo column (0/1)
    price_noise = np.random.normal(0, 0.05, size=(n_rows, len(PRODUCTS)))
    prices_matrix = np.round(base_prices + price_noise, 2)
    prices_matrix = np.clip(prices_matrix, 0.10, None)

    # Expand into tidy records
    records = []
    stores = df["store"].to_numpy()
    dates = df["date"].to_numpy()
    promos = df["on_promo"].to_numpy()

    for prod_idx, prod in enumerate(PRODUCTS):
        sku = prod["sku"]
        sub_df = pd.DataFrame(
            {
                "store": stores,
                "sku": sku,
                "date": dates,
                "units_sold": units_sold_matrix[:, prod_idx],
                "price": prices_matrix[:, prod_idx],
                "on_promo": promos,
            }
        )
        records.append(sub_df)

    df_sales = pd.concat(records, ignore_index=True)

    # 6. Sort by store, sku, date. Drop duplicates on (store, sku, date).
    df_sales = df_sales.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)
    df_sales = df_sales.drop_duplicates(subset=["store", "sku", "date"])

    # Ensure output directory exists and write CSV
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df_sales.to_csv(output_csv_path, index=False)
    print(f"Sample sales written to {output_csv_path}")

    # 7. Print row count, store count, SKU count, and date range
    print(f"Row count: {len(df_sales):,}")
    print(f"Store count: {df_sales['store'].nunique()}")
    print(f"SKU count: {df_sales['sku'].nunique()}")
    print(f"Date range: {df_sales['date'].min()} to {df_sales['date'].max()}")

    return df_sales


if __name__ == "__main__":
    prepare_sample_data()

