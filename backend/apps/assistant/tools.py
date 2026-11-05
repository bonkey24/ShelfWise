"""Tool definitions and implementations for the ShelfWise Assistant."""

from typing import Any, Callable, Dict, List, Optional
from apps.forecasts.models import ForecastResult, ForecastRun
from apps.inventory.models import StockLevel
from apps.inventory.services import compute_inventory_alerts, compute_inventory_summary
from apps.retail.models import Product, Sale, Store


def get_latest_done_run() -> Optional[ForecastRun]:
    """Retrieve the latest completed ForecastRun."""
    return ForecastRun.objects.filter(status="done").order_by("-created_at").first()


def get_model_metrics() -> Dict[str, Any]:
    """Return model evaluation metrics (WAPE, bias, RMSSE) for Naive, Seasonal Naive (28d), and LightGBM."""
    run = get_latest_done_run()
    if not run or not run.metrics:
        return {"error": "No completed forecast run found."}

    m = run.metrics
    return {
        "run_id": run.id,
        "Naive": m.get("Naive", {}),
        "Seasonal Naive (28d)": m.get("Seasonal Naive (28d)", {}),
        "LightGBM": m.get("LightGBM", {}),
    }


def get_inventory_summary() -> Dict[str, Any]:
    """Return portfolio inventory status counts and total suggested order units."""
    run = get_latest_done_run()
    if not run:
        return {"error": "No completed forecast run found."}
    summary = compute_inventory_summary(run=run)
    return {
        "run_id": summary.get("run_id"),
        "counts": summary.get("counts", {}),
        "total_suggested_order_units": round(summary.get("total_suggested_order_units", 0.0), 1),
        "estimated_overstock_units": round(summary.get("estimated_overstock_units", 0.0), 1),
    }


def get_alerts(
    status: Optional[str] = None,
    store: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Return prioritized inventory alerts sorted by severity (stockout_risk, reorder_now, overstock, ok).

    Args:
        status: Filter by status ('stockout_risk', 'reorder_now', 'overstock', 'ok').
        store: Filter by store code (e.g. 'S1097').
        limit: Max items to return (capped at 10).
    """
    run = get_latest_done_run()
    if not run:
        return {"count": 0, "alerts": []}
    safe_limit = min(max(1, int(limit)), 10)
    alerts = compute_inventory_alerts(
        run=run,
        status_filter=status.strip().lower() if status else None,
        store_filter=store.strip().upper() if store else None,
        limit=safe_limit,
    )

    items = []
    for a in alerts:
        items.append(
            {
                "store": a["store"],
                "sku": a["sku"],
                "on_hand": round(a["on_hand"], 1),
                "lead_time_days": a["lead_time_days"],
                "avg_daily_forecast": round(a["avg_daily_forecast"], 1),
                "days_of_cover": a["days_of_cover"],
                "status": a["status"],
                "suggested_order_qty": round(a["suggested_order_qty"], 1),
            }
        )
    return {"count": len(items), "alerts": items}


def get_series_forecast(store: str, sku: str) -> Dict[str, Any]:
    """Return detailed demand history, future 28-day forecast, promo days, and stock for a store/SKU series.

    Args:
        store: Store code (e.g. 'S1097').
        sku: Product SKU code (e.g. 'P1').
    """
    store_code = store.strip().upper()
    sku_code = sku.strip().upper()

    run = get_latest_done_run()
    if not run:
        return {"error": "No completed forecast run available."}

    results = list(
        ForecastResult.objects.filter(
            run=run,
            store__code=store_code,
            product__sku=sku_code,
        ).order_by("date")
    )

    if not results:
        return {"error": f"No forecast results found for store {store_code} and SKU {sku_code}."}

    # Test window actuals vs forecast (last 28 observed days)
    test_rows = [r for r in results if r.actual is not None]
    last_28_actual_total = round(sum(r.actual for r in test_rows), 1)
    last_28_forecast_total = round(sum(r.forecast for r in test_rows), 1)

    # Future 28-day horizon (actual is None)
    future_rows = [r for r in results if r.actual is None]
    next_28_forecast_total = round(sum(r.forecast for r in future_rows), 1)
    next_28_daily_avg = (
        round(next_28_forecast_total / len(future_rows), 1) if future_rows else 0.0
    )

    # Percent change vs last 28 actual days
    if last_28_actual_total > 0:
        percent_change = round(
            ((next_28_forecast_total - last_28_actual_total) / last_28_actual_total) * 100, 1
        )
    else:
        percent_change = 0.0

    # Promo days in next 28 days (under the d - 28 promo recurrence assumption)
    test_dates = [r.date for r in test_rows]
    promo_days_count = Sale.objects.filter(
        store__code=store_code,
        product__sku=sku_code,
        date__in=test_dates,
        on_promo=True,
    ).count()

    # Stock & lead time
    stock = StockLevel.objects.filter(store__code=store_code, product__sku=sku_code).first()
    on_hand = round(stock.on_hand, 1) if stock else 0.0
    lead_time_days = stock.lead_time_days if stock else 7

    return {
        "store": store_code,
        "sku": sku_code,
        "last_28_days_actual_total": last_28_actual_total,
        "last_28_days_forecast_total": last_28_forecast_total,
        "next_28_days_forecast_total": next_28_forecast_total,
        "next_28_days_daily_avg": next_28_daily_avg,
        "percent_change_vs_last_28_actuals": percent_change,
        "next_28_days_promo_days": promo_days_count,
        "lead_time_days": lead_time_days,
        "on_hand": on_hand,
        "stock_level_note": "Stock levels are simulated demo data",
    }


def list_stores_and_skus() -> Dict[str, Any]:
    """Return all available store codes and product SKUs in the catalog."""
    stores = [{"code": s.code, "name": s.name} for s in Store.objects.all().order_by("code")]
    products = [{"sku": p.sku, "name": p.name} for p in Product.objects.all().order_by("sku")]
    return {"stores": stores, "products": products}


# Registry of tool definitions
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "get_model_metrics": get_model_metrics,
    "get_inventory_summary": get_inventory_summary,
    "get_alerts": get_alerts,
    "get_series_forecast": get_series_forecast,
    "list_stores_and_skus": list_stores_and_skus,
}

# Generic schema declarations for LLM providers
TOOL_DECLARATIONS = [
    {
        "name": "get_model_metrics",
        "description": "Get overall forecast model accuracy metrics (WAPE, bias, RMSSE) comparing Naive, Seasonal Naive (28d), and LightGBM.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_inventory_summary",
        "description": "Get portfolio-wide inventory health summary: counts for stockout_risk, reorder_now, overstock, ok, and total suggested order units.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_alerts",
        "description": "Get prioritized inventory replenishment alerts sorted by severity (stockout_risk, reorder_now, overstock, ok).",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional status filter: 'stockout_risk', 'reorder_now', 'overstock', or 'ok'.",
                },
                "store": {
                    "type": "string",
                    "description": "Optional store code to filter by, e.g. 'S1097'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of alerts to return (1-10, default 10).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_series_forecast",
        "description": "Get demand history, next 28-day forecast volume, promo day counts, and inventory stock for a specific store and SKU.",
        "parameters": {
            "type": "object",
            "properties": {
                "store": {
                    "type": "string",
                    "description": "Store code (e.g. 'S1097').",
                },
                "sku": {
                    "type": "string",
                    "description": "Product SKU (e.g. 'P1').",
                },
            },
            "required": ["store", "sku"],
        },
    },
    {
        "name": "list_stores_and_skus",
        "description": "List all active store locations and product SKUs in the ShelfWise catalog.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
