"""CLI script for running ShelfWise demand forecasting and evaluation.

Usage:
    python -m forecasting.run_forecast [data/sample_sales.csv]

Flow:
    1. Loads retail sales CSV dataset.
    2. Performs three-way time split: train / valid (28 days, early stopping) /
       test (28 days, final reporting).
    3. Builds direct 28-day lag features (avoiding test-period leakage).
    4. Trains LightGBM with early stopping on the validation set.
    5. Computes WAPE, Bias, and RMSSE on the TEST set for Naive, Seasonal Naive,
       and LightGBM models.
    6. Prints a per-day diagnostic table for one store/sku showing all forecasts
       alongside actuals.
    7. Saves metrics to backend/forecasting/output/metrics.json.
"""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

from forecasting.baseline import (
    naive_forecast,
    seasonal_naive_28_forecast,
    seasonal_naive_forecast,
)
from forecasting.features import DIRECT_28_FEATURE_COLS, build_features
from forecasting.metrics import bias, rmsse, wape
from forecasting.model import get_feature_importance, predict, train_lgbm
from forecasting.split import three_way_split


def resolve_csv_path(arg_path: str | None) -> Path:
    """Resolve the dataset CSV path flexibly across current working directories."""
    default_rel = "data/sample_sales.csv"
    candidate_str = arg_path if arg_path else default_rel
    candidate = Path(candidate_str)

    if candidate.is_file():
        return candidate.resolve()

    # Try relative to cwd
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.is_file():
        return cwd_candidate.resolve()

    # Try relative to project root (2 levels up from backend/forecasting/)
    project_root = Path(__file__).resolve().parents[2]
    root_candidate = project_root / candidate_str
    if root_candidate.is_file():
        return root_candidate.resolve()

    # Try root data/sample_sales.csv
    root_default = project_root / default_rel
    if root_default.is_file():
        return root_default.resolve()

    raise FileNotFoundError(f"Could not find dataset file at: {candidate_str}")


def main() -> None:
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    csv_file = resolve_csv_path(csv_arg)
    print(f"Loading dataset from: {csv_file}")

    df = pd.read_csv(csv_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)

    print(f"Dataset shape: {df.shape[0]} rows, {df['store'].nunique()} stores, {df['sku'].nunique()} SKUs")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    # 1. Three-way time split (raw data)
    train_raw, valid_raw, test_raw = three_way_split(df, valid_days=28, test_days=28)
    print(
        f"Three-way split: Train={len(train_raw)} rows "
        f"({train_raw['date'].nunique()} days), "
        f"Valid={len(valid_raw)} rows ({valid_raw['date'].nunique()} days), "
        f"Test={len(test_raw)} rows ({test_raw['date'].nunique()} days)"
    )
    print(
        f"  Train: {train_raw['date'].min().date()} to {train_raw['date'].max().date()}"
    )
    print(
        f"  Valid: {valid_raw['date'].min().date()} to {valid_raw['date'].max().date()}"
    )
    print(
        f"  Test : {test_raw['date'].min().date()} to {test_raw['date'].max().date()}"
    )

    # 2. Build features on all data up to end of test
    #    (lags >= 28 ensure test features never access test-period actuals)
    print("Building features (direct 28-day lags)...")
    feat_df = build_features(df)

    # Split features into train / valid / test using the same date boundaries
    train_feat, valid_feat, test_feat = three_way_split(feat_df, valid_days=28, test_days=28)

    # Ground truth for metrics (key-based alignment, zero positional dependency)
    train_plus_valid_raw = pd.concat([train_raw, valid_raw], ignore_index=True)
    y_train_plus_valid = train_plus_valid_raw["units_sold"].to_numpy()

    test_actuals = test_raw[["store", "sku", "date", "units_sold"]].copy()
    test_actuals["store"] = test_actuals["store"].astype(str)
    test_actuals["sku"] = test_actuals["sku"].astype(str)
    test_actuals["date"] = pd.to_datetime(test_actuals["date"])
    n_test = len(test_actuals)

    # 3. Baselines (computed on train+valid history, evaluated on test)
    print("Computing baseline forecasts on test set...")
    naive_df = naive_forecast(train_plus_valid_raw, test_raw)
    snaive_df = seasonal_naive_forecast(train_plus_valid_raw, test_raw)
    snaive28_df = seasonal_naive_28_forecast(train_plus_valid_raw, test_raw)

    # 4. Train LightGBM (train features for fitting, valid features for early stopping)
    print("Training LightGBM regressor with early stopping on validation set...")
    model = train_lgbm(
        train_feat=train_feat,
        valid_feat=valid_feat,
        feature_cols=DIRECT_28_FEATURE_COLS,
        target_col="units_sold",
        n_estimators=600,
        learning_rate=0.05,
        num_leaves=31,
        early_stopping_rounds=50,
        random_state=42,
    )

    lgbm_df = predict(model, test_feat, DIRECT_28_FEATURE_COLS)

    # Ensure consistent typing for keys across all forecast DataFrames
    model_dfs = {
        "Naive": naive_df,
        "Seasonal Naive (7d)": snaive_df,
        "Seasonal Naive (28d)": snaive28_df,
        "LightGBM": lgbm_df,
    }
    for m_name, m_df in model_dfs.items():
        m_df["store"] = m_df["store"].astype(str)
        m_df["sku"] = m_df["sku"].astype(str)
        m_df["date"] = pd.to_datetime(m_df["date"])

    # 5. Key-based merge and evaluation (assert row count == n_test)
    results = {}
    merged_dfs = {}
    for m_name, m_df in model_dfs.items():
        m_merged = pd.merge(test_actuals, m_df, on=["store", "sku", "date"], how="inner")
        assert len(m_merged) == n_test, (
            f"Row count mismatch for {m_name}: expected {n_test}, got {len(m_merged)}"
        )
        merged_dfs[m_name] = m_merged
        y_true = m_merged["units_sold"].to_numpy()
        y_pred = m_merged["forecast"].to_numpy()
        results[m_name] = {
            "WAPE": wape(y_true, y_pred),
            "Bias": bias(y_true, y_pred),
            "RMSSE": rmsse(y_train_plus_valid, y_true, y_pred),
        }

    # Per-store WAPE across ALL models
    stores = sorted(test_actuals["store"].unique())
    store_wapes_all_models = {st: {} for st in stores}
    for m_name, m_merged in merged_dfs.items():
        for st in stores:
            st_data = m_merged[m_merged["store"] == st]
            st_wape = wape(st_data["units_sold"], st_data["forecast"])
            store_wapes_all_models[st][m_name] = st_wape

    # Top 10 feature importances
    feat_imp = get_feature_importance(model, DIRECT_28_FEATURE_COLS)
    top_10 = feat_imp.head(10)

    # 6. Display Clean Tables
    print("\n" + "=" * 66)
    print("           MODEL EVALUATION COMPARISON (TEST SET)             ")
    print("=" * 66)
    print(f"{'Model':<24} | {'WAPE':>10} | {'Bias':>10} | {'RMSSE':>10}")
    print("-" * 66)
    for model_name, m in results.items():
        print(f"{model_name:<24} | {m['WAPE']:>10.4f} | {m['Bias']:>10.4f} | {m['RMSSE']:>10.4f}")
    print("=" * 66)

    print("\n" + "=" * 74)
    print("                     WAPE PER MODEL PER STORE (TEST SET)                  ")
    print("=" * 74)
    print(f"{'Store':<10} | {'Naive':>10} | {'SeasNav7d':>12} | {'SeasNav28d':>12} | {'LightGBM':>10} | {'Winner':>10}")
    print("-" * 74)
    for st, m_wapes in store_wapes_all_models.items():
        n_w = m_wapes["Naive"]
        s7_w = m_wapes["Seasonal Naive (7d)"]
        s28_w = m_wapes["Seasonal Naive (28d)"]
        l_w = m_wapes["LightGBM"]
        winner = min(m_wapes, key=m_wapes.get)
        print(f"{st:<10} | {n_w:>10.4f} | {s7_w:>12.4f} | {s28_w:>12.4f} | {l_w:>10.4f} | {winner:>10}")
    print("=" * 74)

    # Specific check for S1097 P1 across all four models
    diag_store = "S1097" if "S1097" in stores else stores[0]
    diag_sku = "P1"
    s1097_p1_wapes = {}
    for m_name, m_merged in merged_dfs.items():
        sub = m_merged[(m_merged["store"] == diag_store) & (m_merged["sku"] == diag_sku)]
        s1097_p1_wapes[m_name] = wape(sub["units_sold"], sub["forecast"])

    print("\n" + "=" * 66)
    print(f"      WAPE FOR STORE {diag_store}, SKU {diag_sku} (ALL FOUR MODELS)")
    print("=" * 66)
    for m_name, val in s1097_p1_wapes.items():
        print(f"  {m_name:<24} : {val:>10.4f}")
    print("=" * 66)

    print("\n" + "=" * 48)
    print("          TOP 10 FEATURE IMPORTANCES            ")
    print("=" * 48)
    print(f"{'Rank':<5} | {'Feature':<28} | {'Importance':>9}")
    print("-" * 48)
    for idx, row in top_10.iterrows():
        print(f"{idx + 1:<5} | {row['feature']:<28} | {row['importance']:>9.0f}")
    print("=" * 48)

    # 7. Promotional Cycle Diagnostic
    promo_diag = _print_promo_diagnostic(df, diag_store)

    # 8. Per-day diagnostic table for one store/sku (key-based alignment)
    _print_diagnostic(
        train_plus_valid_raw, test_actuals,
        merged_dfs, diag_store, diag_sku,
    )

    # 9. Save to metrics.json
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"

    metrics_payload = {
        "split": "three_way (train / valid_28d / test_28d)",
        "models": results,
        "per_store_wape": store_wapes_all_models,
        "s1097_p1_wape": s1097_p1_wapes,
        "top_10_features": top_10.to_dict(orient="records"),
        "promo_diagnostic": promo_diag,
        "best_iteration": int(model.best_iteration_) if hasattr(model, "best_iteration_") else None,
        "validation_days": 28,
        "test_days": 28,
        "dataset_rows": len(df),
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\nMetrics saved to: {metrics_path}\n")


def _print_promo_diagnostic(df: pd.DataFrame, store: str) -> dict:
    """Print promo diagnostic: impact on units_sold and weekly promo frequency."""
    print("\n" + "=" * 68)
    print(f"      PROMOTIONAL CYCLE DIAGNOSTIC (Store: {store})")
    print("=" * 68)

    # 1. Mean units_sold for on_promo=1 vs on_promo=0
    mean_p1_all = float(df[df["on_promo"] == 1]["units_sold"].mean())
    mean_p0_all = float(df[df["on_promo"] == 0]["units_sold"].mean())
    ratio_all = mean_p1_all / mean_p0_all if mean_p0_all > 0 else float("nan")

    store_df = df[df["store"] == store]
    mean_p1_store = float(store_df[store_df["on_promo"] == 1]["units_sold"].mean())
    mean_p0_store = float(store_df[store_df["on_promo"] == 0]["units_sold"].mean())
    ratio_store = mean_p1_store / mean_p0_store if mean_p0_store > 0 else float("nan")

    print("  Mean units_sold:")
    print(f"    - All stores: on_promo=1: {mean_p1_all:.1f} | on_promo=0: {mean_p0_all:.1f} (Lift: {ratio_all:.2f}x)")
    print(f"    - Store {store}: on_promo=1: {mean_p1_store:.1f} | on_promo=0: {mean_p0_store:.1f} (Lift: {ratio_store:.2f}x)")

    # 2. Number of promo days in each of the last 8 weeks for the store
    store_dates = (
        store_df[["date", "on_promo"]]
        .drop_duplicates(subset=["date"])
        .sort_values(by="date")
        .reset_index(drop=True)
    )

    last_56_days = store_dates.tail(56).copy().reset_index(drop=True)
    weekly_promo_counts = []

    print("\n  Promo days in each of the last 8 weeks (7-day blocks ending at dataset max date):")
    print(f"  {'Week':<8} | {'Date Range':<25} | {'Promo Days':>10}")
    print(f"  {'-' * 49}")

    for w in range(8):
        chunk = last_56_days.iloc[w * 7 : (w + 1) * 7]
        if chunk.empty:
            continue
        start_d = chunk["date"].min().date()
        end_d = chunk["date"].max().date()
        promo_days = int(chunk["on_promo"].sum())
        week_num = w + 1
        weekly_promo_counts.append({
            "week": week_num,
            "start_date": str(start_d),
            "end_date": str(end_d),
            "promo_days": promo_days,
        })
        print(f"  Week {week_num:<3} | {str(start_d)} to {str(end_d):<12} | {promo_days:>10}")

    print("=" * 68)
    return {
        "mean_units_sold_promo_1_all": mean_p1_all,
        "mean_units_sold_promo_0_all": mean_p0_all,
        "mean_units_sold_promo_1_store": mean_p1_store,
        "mean_units_sold_promo_0_store": mean_p0_store,
        "last_8_weeks_promo_days": weekly_promo_counts,
    }


def _print_diagnostic(
    history: pd.DataFrame,
    test_actuals: pd.DataFrame,
    merged_dfs: dict[str, pd.DataFrame],
    store: str,
    sku: str,
) -> None:
    """Print a per-day diagnostic showing last 14 train values and 28 test forecasts (all key-aligned)."""
    hist = history.copy()
    hist["date"] = pd.to_datetime(hist["date"])
    hist_ss = hist[(hist["store"] == store) & (hist["sku"] == sku)].sort_values("date")
    last_14_train = hist_ss.tail(14)[["date", "units_sold"]].copy()

    test_ss = test_actuals[(test_actuals["store"] == store) & (test_actuals["sku"] == sku)].sort_values("date")
    dates_list = test_ss["date"].tolist()
    actuals = test_ss["units_sold"].tolist()

    naive_vals = merged_dfs["Naive"][
        (merged_dfs["Naive"]["store"] == store) & (merged_dfs["Naive"]["sku"] == sku)
    ].sort_values("date")["forecast"].tolist()

    snaive_vals = merged_dfs["Seasonal Naive (7d)"][
        (merged_dfs["Seasonal Naive (7d)"]["store"] == store) & (merged_dfs["Seasonal Naive (7d)"]["sku"] == sku)
    ].sort_values("date")["forecast"].tolist()

    snaive28_vals = merged_dfs["Seasonal Naive (28d)"][
        (merged_dfs["Seasonal Naive (28d)"]["store"] == store) & (merged_dfs["Seasonal Naive (28d)"]["sku"] == sku)
    ].sort_values("date")["forecast"].tolist()

    lgbm_vals = merged_dfs["LightGBM"][
        (merged_dfs["LightGBM"]["store"] == store) & (merged_dfs["LightGBM"]["sku"] == sku)
    ].sort_values("date")["forecast"].tolist()

    header = f"\n{'=' * 98}\n  DIAGNOSTIC: store={store}, sku={sku}\n{'=' * 98}"
    print(header)

    # Last 14 training days
    print(f"\n  Last 14 training days:")
    print(f"  {'Date':<12} | {'DoW':<4} | {'Actual':>10}")
    print(f"  {'-' * 34}")
    for _, row in last_14_train.iterrows():
        dow = row["date"].strftime("%a")
        print(f"  {str(row['date'].date()):<12} | {dow:<4} | {row['units_sold']:>10.1f}")

    # Test period (28 days)
    print(f"\n  Test period (28 days): actual vs forecasts (key-aligned)")
    print(
        f"  {'Date':<12} | {'DoW':<4} | {'Actual':>10} | {'Naive':>10} | "
        f"{'SeasNav7d':>10} | {'SeasNav28d':>10} | {'LightGBM':>10}"
    )
    print(f"  {'-' * 85}")

    for i, d in enumerate(dates_list):
        dow = d.strftime("%a")
        actual_v = actuals[i]
        naive_v = naive_vals[i] if i < len(naive_vals) else float("nan")
        snaive_v = snaive_vals[i] if i < len(snaive_vals) else float("nan")
        snaive28_v = snaive28_vals[i] if i < len(snaive28_vals) else float("nan")
        lgbm_v = lgbm_vals[i] if i < len(lgbm_vals) else float("nan")
        print(
            f"  {str(d.date()):<12} | {dow:<4} | {actual_v:>10.1f} | {naive_v:>10.1f} | "
            f"{snaive_v:>10.1f} | {snaive28_v:>10.1f} | {lgbm_v:>10.1f}"
        )

    print("=" * 98)


if __name__ == "__main__":
    main()
