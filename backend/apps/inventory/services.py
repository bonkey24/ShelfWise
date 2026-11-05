"""Service layer for inventory optimization analytics and alert generation."""

import math
from typing import Any
import pandas as pd

from apps.forecasts.models import ForecastResult, ForecastRun
from apps.inventory.models import StockLevel
from forecasting.inventory import (
    classify,
    reorder_point,
    safety_stock,
    suggested_order_qty,
)

SEVERITY_ORDER = {
    "stockout_risk": 0,
    "reorder_now": 1,
    "overstock": 2,
    "ok": 3,
}


def get_forecast_run(run_id: int | str | None = None) -> ForecastRun:
    """Retrieve the specified ForecastRun or the latest completed run."""
    if run_id is not None and str(run_id).strip() != "":
        return ForecastRun.objects.get(id=int(run_id))

    latest_run = (
        ForecastRun.objects.filter(status="done")
        .order_by("-finished_at", "-created_at")
        .first()
    )
    if not latest_run:
        raise ForecastRun.DoesNotExist("No completed forecast runs found.")
    return latest_run


def compute_inventory_alerts(
    run: ForecastRun,
    status_filter: str | None = None,
    store_filter: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    """Compute store/SKU inventory risk alerts and replenishment metrics for a forecast run.

    Queries ForecastResult and StockLevel in bulk (single query each) and computes:
    - sigma_daily: sample std of (actual - forecast) on test window rows
    - lead_time_demand: sum of future forecasts over lead_time_days
    - avg_daily_forecast: mean forecast of future horizon
    - safety_stock, reorder_point, status, suggested_order_qty

    Results are sorted by severity: stockout_risk, reorder_now, overstock, ok.
    """
    # 1. Load results in a single query
    res_qs = ForecastResult.objects.filter(run=run).values(
        "store__code", "product__sku", "date", "forecast", "actual"
    )
    res_list = list(res_qs)
    if not res_list:
        return []

    df_res = pd.DataFrame(res_list).rename(
        columns={"store__code": "store", "product__sku": "sku"}
    )

    # 2. Load stock levels in a single query
    stocks_qs = StockLevel.objects.values(
        "id", "store__code", "product__sku", "on_hand", "lead_time_days", "service_level"
    )
    stocks_list = list(stocks_qs)
    if not stocks_list:
        return []

    df_stocks = pd.DataFrame(stocks_list).rename(
        columns={"store__code": "store", "product__sku": "sku"}
    )

    # Separate test-window rows (actual is present) and future horizon rows (actual is null)
    test_df = df_res[df_res["actual"].notna()].copy()
    future_df = df_res[df_res["actual"].isna()].copy()
    future_df = future_df.sort_values(by=["store", "sku", "date"])

    # Calculate test-window residual standard deviation per series
    test_df["residual"] = test_df["actual"] - test_df["forecast"]
    sigmas = (
        test_df.groupby(["store", "sku"])["residual"]
        .apply(lambda s: float(s.std(ddof=1)) if len(s) > 1 else 0.0)
        .to_dict()
    )

    # Pre-index future forecasts by (store, sku)
    future_forecasts_map = (
        future_df.groupby(["store", "sku"])["forecast"]
        .apply(lambda s: s.to_numpy())
        .to_dict()
    )

    alerts: list[dict[str, Any]] = []

    for _, row in df_stocks.iterrows():
        st = str(row["store"])
        sk = str(row["sku"])
        on_hand = float(row["on_hand"])
        lead_time_days = int(row["lead_time_days"])
        service_level = float(row["service_level"])

        sigma = sigmas.get((st, sk), 0.0)
        if math.isnan(sigma) or sigma < 0:
            sigma = 0.0

        future_vals = future_forecasts_map.get((st, sk), None)
        if future_vals is not None and len(future_vals) > 0:
            avg_daily = float(future_vals.mean())
            if len(future_vals) >= lead_time_days:
                ltd = float(future_vals[:lead_time_days].sum())
            else:
                ltd = float(future_vals.sum() + (lead_time_days - len(future_vals)) * avg_daily)

            if len(future_vals) >= 7:
                rpd = float(future_vals[:7].sum())
            else:
                rpd = float(future_vals.sum() + (7 - len(future_vals)) * avg_daily)
        else:
            avg_daily = 0.0
            ltd = 0.0
            rpd = 0.0

        ss = safety_stock(sigma_daily=sigma, lead_time_days=lead_time_days, service_level=service_level)
        rop = reorder_point(lead_time_demand=ltd, safety_stock=ss)
        status = classify(
            on_hand=on_hand,
            lead_time_demand=ltd,
            rop=rop,
            avg_daily_forecast=avg_daily,
        )
        order_qty = suggested_order_qty(on_hand=on_hand, rop=rop, review_period_demand=rpd)
        doc = round(on_hand / avg_daily, 1) if avg_daily > 0 else (999.0 if on_hand > 0 else 0.0)

        alert_item = {
            "stock_id": int(row["id"]) if "id" in row and pd.notna(row["id"]) else None,
            "store": st,
            "sku": sk,
            "on_hand": round(on_hand, 1),
            "lead_time_days": lead_time_days,
            "avg_daily_forecast": round(avg_daily, 1),
            "lead_time_demand": round(ltd, 1),
            "safety_stock": round(ss, 1),
            "reorder_point": round(rop, 1),
            "days_of_cover": doc,
            "status": status,
            "suggested_order_qty": round(order_qty, 1),
        }
        alerts.append(alert_item)

    # Sort by severity: stockout_risk, reorder_now, overstock, ok; then by days of cover
    alerts.sort(
        key=lambda x: (
            SEVERITY_ORDER.get(x["status"], 99),
            x["days_of_cover"],
            x["store"],
            x["sku"],
        )
    )

    # Apply filters
    if status_filter:
        alerts = [a for a in alerts if a["status"].lower() == status_filter.lower()]

    if store_filter:
        alerts = [a for a in alerts if a["store"].lower() == store_filter.lower()]

    if offset is not None and offset > 0:
        alerts = alerts[offset:]

    if limit is not None and limit > 0:
        alerts = alerts[:limit]

    return alerts


def compute_inventory_summary(run: ForecastRun) -> dict[str, Any]:
    """Compute portfolio-level inventory risk and replenishment summary."""
    all_alerts = compute_inventory_alerts(run=run)

    counts = {
        "stockout_risk": 0,
        "reorder_now": 0,
        "overstock": 0,
        "ok": 0,
    }
    for item in all_alerts:
        st = item["status"]
        if st in counts:
            counts[st] += 1
        else:
            counts[st] = 1

    total_suggested_order_units = round(
        sum(item["suggested_order_qty"] for item in all_alerts), 1
    )

    # Estimated overstock units: on_hand - lead_time_demand - safety_stock (overstock rows only)
    estimated_overstock_units = round(
        sum(
            max(0.0, item["on_hand"] - item["lead_time_demand"] - item["safety_stock"])
            for item in all_alerts
            if item["status"] == "overstock"
        ),
        1,
    )

    return {
        "run_id": run.id,
        "counts": counts,
        "status_counts": counts,
        "total_suggested_order_units": total_suggested_order_units,
        "estimated_overstock_units": estimated_overstock_units,
    }

