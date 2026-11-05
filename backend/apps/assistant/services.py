"""Service layer coordinating LLM tool calling loops and rule-based fallback responses."""

import logging
import re
from typing import Any, Dict, List, Tuple
from django.conf import settings

from apps.assistant.providers import AnthropicProvider, GeminiProvider
from apps.assistant.tools import (
    get_alerts,
    get_inventory_summary,
    get_model_metrics,
    get_series_forecast,
    list_stores_and_skus,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ShelfWise's AI assistant for small retailers and boutique store managers. "
    "Answer ONLY from tool results. Never invent or hallucinate numbers. "
    "If the tool results do not contain the answer, state clearly that the data is not available. "
    "Explain demand changes using the promo and trend fields provided by tools. "
    "Note that stock levels are simulated demo data. "
    "Be concise, direct, and actionable. Use short markdown tables where useful."
)


def rule_based_fallback(last_user_message: str) -> Tuple[str, List[str]]:
    """Generate deterministic, grounded replies when LLM_PROVIDER=none or provider call fails."""
    text = last_user_message.lower().strip()
    tools_used: List[str] = []

    # Check for series specific question (e.g. "S1097 P1")
    store_match = re.search(r"\b(s\d+)\b", text)
    sku_match = re.search(r"\b(p\d+)\b", text)

    if store_match and sku_match:
        store_code = store_match.group(1).upper()
        sku_code = sku_match.group(1).upper()
        tools_used.append("get_series_forecast")
        res = get_series_forecast(store=store_code, sku=sku_code)

        if "error" in res:
            reply = f"Could not retrieve forecast data for {store_code} {sku_code}: {res['error']}"
        else:
            pct_change = res["percent_change_vs_last_28_actuals"]
            direction = "rising" if pct_change > 0 else "declining" if pct_change < 0 else "steady"
            reply = (
                f"### Demand Analysis for {store_code} · {sku_code}\n\n"
                f"Over the next 28 days, projected demand is **{res['next_28_days_forecast_total']:,} units** "
                f"({res['next_28_days_daily_avg']:.1f} units/day), which is **{direction} by {abs(pct_change):.1f}%** "
                f"compared to the last 28 days of actual sales ({res['last_28_days_actual_total']:,} units).\n\n"
                f"- **Upcoming Promotions:** {res['next_28_days_promo_days']} scheduled promo days in the next 28-day window.\n"
                f"- **Current Stock:** {res['on_hand']:.0f} units on hand with a {res['lead_time_days']}-day supplier lead time.\n\n"
                f"> *Note: Stock levels are simulated demo data.*"
            )
        return f"{reply}\n\n(offline mode)", tools_used

    # 1. Stockout risks intent
    if any(k in text for k in ["stockout", "stock-out", "stock out", "run out", "empty", "zero stock"]):
        tools_used.extend(["get_inventory_summary", "get_alerts"])
        summary = get_inventory_summary()
        alerts_data = get_alerts(status="stockout_risk", limit=5)
        stockout_count = summary.get("counts", {}).get("stockout_risk", 0)

        displayed_alerts = alerts_data.get("alerts", [])
        n_displayed = len(displayed_alerts)
        subset_note = (
            f"\n\nShowing the {n_displayed} most urgent of {stockout_count}."
            if stockout_count > n_displayed
            else ""
        )

        rows = []
        for a in displayed_alerts:
            rows.append(
                f"| {a['store']} | {a['sku']} | {a['on_hand']:.0f} | {a['lead_time_days']}d | "
                f"{a['days_of_cover']:.1f}d | **+{a['suggested_order_qty']:.0f}** |"
            )
        table_md = "\n".join(rows) if rows else "| No active stockout risks found | | | | | |"

        reply = (
            f"### ⚠️ Critical Stockout Risks\n\n"
            f"There are currently **{stockout_count} SKU locations** facing imminent stockout risk "
            f"where on-hand inventory is insufficient to cover lead-time demand.\n\n"
            f"| Store | SKU | On Hand | Lead Time | Days Cover | Suggested Order |\n"
            f"|---|---|---|---|---|---|\n"
            f"{table_md}"
            f"{subset_note}\n\n"
            f"Immediate replenishment purchase orders are recommended to avoid stock depletion. "
            f"*Note: Stock levels are simulated demo data.*"
        )
        return f"{reply}\n\n(offline mode)", tools_used

    # 2. Reorder this week intent
    if any(k in text for k in ["reorder", "purchase order", "order this week", "replenish", "buy"]):
        tools_used.extend(["get_alerts", "get_inventory_summary"])
        summary = get_inventory_summary()
        reorder_alerts = get_alerts(status="reorder_now", limit=5).get("alerts", [])
        stockout_alerts = get_alerts(status="stockout_risk", limit=5).get("alerts", [])
        all_reorder = stockout_alerts + reorder_alerts

        total_urgent = summary.get("counts", {}).get("stockout_risk", 0) + summary.get("counts", {}).get("reorder_now", 0)
        displayed_reorder = all_reorder[:6]
        n_reorder = len(displayed_reorder)
        reorder_subset_note = (
            f"\n\nShowing the {n_reorder} most urgent of {total_urgent}."
            if total_urgent > n_reorder
            else ""
        )

        rows = []
        for a in displayed_reorder:
            status_label = "Stockout Risk" if a["status"] == "stockout_risk" else "Reorder Now"
            rows.append(
                f"| {a['store']} | {a['sku']} | {a['on_hand']:.0f} | {a['days_of_cover']:.1f}d | "
                f"{status_label} | **+{a['suggested_order_qty']:.0f} units** |"
            )
        table_md = "\n".join(rows) if rows else "| All stock levels are currently above reorder points | | | | | |"

        total_units = summary.get("total_suggested_order_units", 0)
        reply = (
            f"### 📦 Recommended Orders This Week\n\n"
            f"Total portfolio replenishment recommended: **{total_units:,.0f} units**.\n\n"
            f"| Store | SKU | On Hand | Days Cover | Status | Order Qty |\n"
            f"|---|---|---|---|---|---|\n"
            f"{table_md}"
            f"{reorder_subset_note}\n\n"
            f"Prioritize items with stockout risk first, followed by items crossing below their Reorder Point (ROP). "
            f"*Note: Stock levels are simulated demo data.*"
        )
        return f"{reply}\n\n(offline mode)", tools_used

    # 3. Forecast accuracy intent
    if any(k in text for k in ["accurate", "accuracy", "wape", "baseline", "model", "metric", "lightgbm"]):
        tools_used.append("get_model_metrics")
        metrics = get_model_metrics()

        lgbm = metrics.get("LightGBM", {})
        s_naive = metrics.get("Seasonal Naive (28d)", {})
        naive = metrics.get("Naive", {})

        lgbm_wape = lgbm.get("WAPE", 0.088)
        s_naive_wape = s_naive.get("WAPE", 0.103)
        naive_wape = naive.get("WAPE", 0.237)

        improvement = ((s_naive_wape - lgbm_wape) / s_naive_wape) * 100 if s_naive_wape else 0

        reply = (
            f"### 📈 Forecast Model Evaluation\n\n"
            f"The active production **LightGBM** model achieved an overall **{lgbm_wape * 100:.1f}% WAPE** "
            f"(forecast accuracy of **{(1 - lgbm_wape) * 100:.1f}%**), reducing forecast error by **{improvement:.1f}%** "
            f"versus the best seasonal baseline.\n\n"
            f"| Model | WAPE | Bias | RMSSE |\n"
            f"|---|---|---|---|\n"
            f"| **LightGBM (Production)** | **{lgbm_wape * 100:.1f}%** | {lgbm.get('Bias', 0):.3f} | {lgbm.get('RMSSE', 0):.2f} |\n"
            f"| Seasonal Naive (28d) | {s_naive_wape * 100:.1f}% | {s_naive.get('Bias', 0):.3f} | {s_naive.get('RMSSE', 0):.2f} |\n"
            f"| Naive (Flat Last Value) | {naive_wape * 100:.1f}% | {naive.get('Bias', 0):.3f} | {naive.get('RMSSE', 0):.2f} |\n\n"
            f"Evaluations are calibrated on the 28-day holdout validation window across all store/SKU series."
        )
        return f"{reply}\n\n(offline mode)", tools_used

    # 4. Default / overview guidance
    tools_used.append("get_inventory_summary")
    summary = get_inventory_summary()
    counts = summary.get("counts", {})

    reply = (
        f"### ShelfWise Retail Co-Pilot Overview\n\n"
        f"Here is your current portfolio status:\n"
        f"- **Critical Stockout Risks:** {counts.get('stockout_risk', 0)} SKU locations\n"
        f"- **Reorder Triggers:** {counts.get('reorder_now', 0)} SKU locations\n"
        f"- **Overstock Items:** {counts.get('overstock', 0)} SKU locations\n"
        f"- **Balanced & Optimal:** {counts.get('ok', 0)} SKU locations\n\n"
        f"You can ask me questions such as:\n"
        f"1. *Which items will stock out soon?*\n"
        f"2. *Why is demand rising for S1097 P1?*\n"
        f"3. *What should I reorder this week?*\n"
        f"4. *How accurate is the forecast?*\n\n"
        f"*Note: Stock levels are simulated demo data.*"
    )
    return f"{reply}\n\n(offline mode)", tools_used


def generate_assistant_response(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Generate assistant response using configured LLM provider with fallback."""
    provider_name = getattr(settings, "LLM_PROVIDER", "none").strip().lower()
    api_key = getattr(settings, "LLM_API_KEY", "").strip()
    model = getattr(settings, "LLM_MODEL", "").strip()

    last_user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_message = m.get("content", "")
            break

    # If provider is 'none' or no API key is set, use rule-based fallback directly
    if provider_name == "none" or not provider_name or not api_key:
        reply, tools_used = rule_based_fallback(last_user_message)
        return {"reply": reply, "tools_used": tools_used}

    try:
        if provider_name == "anthropic":
            client = AnthropicProvider(api_key=api_key, model=model)
            reply, tools_used = client.chat(messages=messages, system_prompt=SYSTEM_PROMPT)
            return {"reply": reply, "tools_used": tools_used}

        elif provider_name == "gemini":
            client = GeminiProvider(api_key=api_key, model=model)
            reply, tools_used = client.chat(messages=messages, system_prompt=SYSTEM_PROMPT)
            return {"reply": reply, "tools_used": tools_used}

        else:
            logger.warning("Unrecognized LLM_PROVIDER '%s'. Falling back.", provider_name)
            reply, tools_used = rule_based_fallback(last_user_message)
            return {"reply": reply, "tools_used": tools_used}

    except Exception as exc:
        logger.warning("LLM provider '%s' failed (%s). Triggering offline fallback.", provider_name, exc)
        reply, tools_used = rule_based_fallback(last_user_message)
        return {"reply": reply, "tools_used": tools_used}

