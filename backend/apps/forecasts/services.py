"""Demand forecasting service integrating pure-Python forecasting module with Django ORM."""

from datetime import datetime
import logging
from typing import Any
from django.db import transaction
from django.utils import timezone
from lightgbm import LGBMRegressor
import numpy as np
import pandas as pd

from apps.forecasts.models import ForecastResult, ForecastRun
from apps.retail.models import Product, Sale, Store
from forecasting.baseline import naive_forecast, seasonal_naive_28_forecast
from forecasting.features import DIRECT_28_FEATURE_COLS, build_features
from forecasting.metrics import bias, rmsse, wape
from forecasting.model import predict, train_lgbm
from forecasting.split import three_way_split

logger = logging.getLogger(__name__)


def run_forecast(run_id: int) -> ForecastRun | None:
    """Execute end-to-end forecasting pipeline for a ForecastRun.

    Pipeline Steps:
    1. Loads all Sale records into a Pandas DataFrame.
    2. Performs three-way time-split (train / valid=horizon / test=horizon).
    3. Trains LightGBM with early stopping on the validation set.
    4. Evaluates Naive, Seasonal Naive (28d), and LightGBM models on the test window
       using key-based alignment (store, sku, date). Saves metrics to run.metrics.
    5. Computes empirical 10th and 90th percentile prediction interval residuals
       per store on the test window.
    6. Refits LightGBM on all historical observations using the best iteration count.
    7. Forecasts the next `horizon_days` beyond the latest historical date under:
       - Future promo assumption: on_promo is assumed identical to 28 days earlier (d - 28).
       - Future price assumption: price is assumed equal to the last known historical price.
    8. Persists both test-window results (with actual units_sold) and future results
       (actual=None) to ForecastResult in bulk.

    Args:
        run_id: Primary key of the ForecastRun instance.

    Returns:
        ForecastRun: Updated model instance with status 'done' or 'failed', or None.
    """
    try:
        run = ForecastRun.objects.get(id=run_id)
    except ForecastRun.DoesNotExist:
        logger.warning("ForecastRun %s does not exist, aborting.", run_id)
        return None
    run = ForecastRun.objects.get(id=run_id)
    run.status = "running"
    run.error = ""
    run.save(update_fields=["status", "error"])

    try:
        horizon = run.horizon_days

        # 1. Load Sale rows from database
        qs = Sale.objects.select_related("store", "product").values(
            "store__code", "product__sku", "date", "units_sold", "price", "on_promo"
        )
        sales_list = list(qs)
        if not sales_list:
            raise ValueError("No sales data available in the database to run forecast.")

        df = pd.DataFrame(sales_list)
        df = df.rename(columns={"store__code": "store", "product__sku": "sku"})
        df["date"] = pd.to_datetime(df["date"])
        df["on_promo"] = df["on_promo"].astype(int)
        df["price"] = df.groupby(["store", "sku"])["price"].ffill().bfill().fillna(0.0)
        df = df.sort_values(by=["store", "sku", "date"]).reset_index(drop=True)

        # 2. Three-way time split
        train_raw, valid_raw, test_raw = three_way_split(df, valid_days=horizon, test_days=horizon)
        train_plus_valid_raw = pd.concat([train_raw, valid_raw], ignore_index=True)
        y_train_plus_valid = train_plus_valid_raw["units_sold"].to_numpy()

        # Build features for historical data
        feat_df = build_features(df)
        train_feat, valid_feat, test_feat = three_way_split(feat_df, valid_days=horizon, test_days=horizon)

        # 3. Train LightGBM with early stopping
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
        best_iteration = getattr(model, "best_iteration_", None) or 600

        # 4. Compute comparison metrics on test window with key-based inner joins
        test_actuals = test_raw[["store", "sku", "date", "units_sold"]].copy()
        test_actuals["store"] = test_actuals["store"].astype(str)
        test_actuals["sku"] = test_actuals["sku"].astype(str)
        test_actuals["date"] = pd.to_datetime(test_actuals["date"])
        n_test = len(test_actuals)

        naive_df = naive_forecast(train_plus_valid_raw, test_raw)
        snaive28_df = seasonal_naive_28_forecast(train_plus_valid_raw, test_raw)
        lgbm_test_df = predict(model, test_feat, DIRECT_28_FEATURE_COLS)

        merged_naive = pd.merge(test_actuals, naive_df, on=["store", "sku", "date"], how="inner")
        assert len(merged_naive) == n_test, f"Naive forecast size mismatch: {len(merged_naive)} vs {n_test}"

        merged_snaive28 = pd.merge(test_actuals, snaive28_df, on=["store", "sku", "date"], how="inner")
        assert len(merged_snaive28) == n_test, f"Seasonal Naive 28d size mismatch: {len(merged_snaive28)} vs {n_test}"

        merged_lgbm = pd.merge(test_actuals, lgbm_test_df, on=["store", "sku", "date"], how="inner")
        assert len(merged_lgbm) == n_test, f"LightGBM test size mismatch: {len(merged_lgbm)} vs {n_test}"

        run.metrics = {
            "Naive": {
                "WAPE": wape(merged_naive["units_sold"], merged_naive["forecast"]),
                "Bias": bias(merged_naive["units_sold"], merged_naive["forecast"]),
                "RMSSE": rmsse(y_train_plus_valid, merged_naive["units_sold"], merged_naive["forecast"]),
            },
            "Seasonal Naive (28d)": {
                "WAPE": wape(merged_snaive28["units_sold"], merged_snaive28["forecast"]),
                "Bias": bias(merged_snaive28["units_sold"], merged_snaive28["forecast"]),
                "RMSSE": rmsse(y_train_plus_valid, merged_snaive28["units_sold"], merged_snaive28["forecast"]),
            },
            "LightGBM": {
                "WAPE": wape(merged_lgbm["units_sold"], merged_lgbm["forecast"]),
                "Bias": bias(merged_lgbm["units_sold"], merged_lgbm["forecast"]),
                "RMSSE": rmsse(y_train_plus_valid, merged_lgbm["units_sold"], merged_lgbm["forecast"]),
            },
            "best_iteration": best_iteration,
        }

        # 5. Prediction intervals: 10th and 90th percentile of test residuals per store
        merged_lgbm["residual"] = merged_lgbm["units_sold"] - merged_lgbm["forecast"]
        store_residuals = {}
        for st, grp in merged_lgbm.groupby("store"):
            resids = grp["residual"].to_numpy()
            q10 = float(np.percentile(resids, 10))
            q90 = float(np.percentile(resids, 90))
            store_residuals[st] = (q10, q90)

        all_resids = merged_lgbm["residual"].to_numpy()
        default_q10 = float(np.percentile(all_resids, 10))
        default_q90 = float(np.percentile(all_resids, 90))

        # 6. Refit on all historical data with best_iteration
        all_clean = feat_df.dropna(subset=DIRECT_28_FEATURE_COLS + ["units_sold"]).copy()
        for c in ["store", "sku"]:
            all_clean[c] = all_clean[c].astype("category")

        refit_model = LGBMRegressor(
            objective="regression",
            n_estimators=best_iteration,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
        refit_model.fit(
            all_clean[DIRECT_28_FEATURE_COLS],
            all_clean["units_sold"].to_numpy(),
            categorical_feature=["store", "sku"],
        )

        # 7. Generate future horizon predictions (next horizon_days)
        # Assumptions:
        # - Future promo flag: same as 28 days earlier (preserves 2-week promo cycle phase)
        # - Future price: last known price per (store, sku)
        max_date = df["date"].max()
        future_dates = pd.date_range(
            start=max_date + pd.Timedelta(days=1),
            periods=horizon,
            freq="D",
        )

        # Build promo lookup for date d - 28
        promo_lookup = {
            (str(r["store"]), str(r["sku"]), pd.to_datetime(r["date"])): int(r["on_promo"])
            for r in df[["store", "sku", "date", "on_promo"]].to_dict("records")
        }

        # Last known price lookup
        last_price_lookup = (
            df.sort_values("date")
            .groupby(["store", "sku"])["price"]
            .last()
            .to_dict()
        )

        unique_combos = df[["store", "sku"]].drop_duplicates().to_dict("records")
        future_rows = []
        for combo in unique_combos:
            st = str(combo["store"])
            sk = str(combo["sku"])
            p_last = float(last_price_lookup.get((st, sk), 0.0))
            for f_date in future_dates:
                ref_date = f_date - pd.Timedelta(days=28)
                f_promo = promo_lookup.get((st, sk, ref_date), 0)
                future_rows.append(
                    {
                        "store": st,
                        "sku": sk,
                        "date": f_date,
                        "units_sold": 0.0,  # placeholder, never used at lags >= 28
                        "price": p_last,
                        "on_promo": f_promo,
                    }
                )

        future_df = pd.DataFrame(future_rows)
        combined_df = pd.concat([df, future_df], ignore_index=True)
        combined_feat = build_features(combined_df)

        future_feat = combined_feat[combined_feat["date"] > max_date].copy().reset_index(drop=True)
        future_preds_df = predict(refit_model, future_feat, DIRECT_28_FEATURE_COLS)

        # 8. Prepare ForecastResult objects for bulk creation
        store_map = {s.code: s for s in Store.objects.all()}
        product_map = {p.sku: p for p in Product.objects.all()}

        results_to_create = []

        # (a) Test-window predictions (actual filled in)
        for _, row in merged_lgbm.iterrows():
            st_code = str(row["store"])
            sku_code = str(row["sku"])
            st_obj = store_map[st_code]
            prod_obj = product_map[sku_code]
            q10, q90 = store_residuals.get(st_code, (default_q10, default_q90))

            fc = float(row["forecast"])
            lower = float(np.clip(fc + q10, 0.0, None))
            upper = float(np.clip(fc + q90, 0.0, None))
            actual = float(row["units_sold"])
            d_val = row["date"].date() if hasattr(row["date"], "date") else row["date"]

            results_to_create.append(
                ForecastResult(
                    run=run,
                    store=st_obj,
                    product=prod_obj,
                    date=d_val,
                    forecast=fc,
                    lower=lower,
                    upper=upper,
                    actual=actual,
                )
            )

        # (b) Future predictions (actual=None)
        for _, row in future_preds_df.iterrows():
            st_code = str(row["store"])
            sku_code = str(row["sku"])
            st_obj = store_map[st_code]
            prod_obj = product_map[sku_code]
            q10, q90 = store_residuals.get(st_code, (default_q10, default_q90))

            fc = float(row["forecast"])
            lower = float(np.clip(fc + q10, 0.0, None))
            upper = float(np.clip(fc + q90, 0.0, None))
            d_val = row["date"].date() if hasattr(row["date"], "date") else row["date"]

            results_to_create.append(
                ForecastResult(
                    run=run,
                    store=st_obj,
                    product=prod_obj,
                    date=d_val,
                    forecast=fc,
                    lower=lower,
                    upper=upper,
                    actual=None,
                )
            )

        # Transactional bulk write
        with transaction.atomic():
            ForecastResult.objects.filter(run=run).delete()
            ForecastResult.objects.bulk_create(results_to_create, batch_size=5000)

            run.status = "done"
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "metrics", "finished_at"])

        return run

    except Exception as exc:
        logger.exception("Forecast run %s failed: %s", run_id, exc)
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        raise exc


def cleanup_stale_runs() -> int:
    """Mark any forecast run in 'running' status older than 10 minutes as failed.

    Used when listing or fetching runs to prevent orphaned runs after a server restart.
    """
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(minutes=10)
    updated = ForecastRun.objects.filter(
        status="running",
        created_at__lt=cutoff,
    ).update(
        status="failed",
        error="Interrupted (server restart or timeout)",
        finished_at=timezone.now(),
    )
    return updated


