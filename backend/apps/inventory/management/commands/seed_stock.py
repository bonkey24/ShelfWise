"""Management command to seed inventory stock levels with realistic scenario variety."""

import random
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.forecasts.models import ForecastResult, ForecastRun
from apps.inventory.models import StockLevel
from apps.retail.models import Product, Sale, Store
from forecasting.inventory import classify, reorder_point, safety_stock


class Command(BaseCommand):
    """Seed stock levels with diverse scenarios per store and SKU."""

    help = (
        "Seed stock levels for all store and SKU combinations using independent deterministic "
        "RNGs per series, assigning scenarios: stockout risk 20%, reorder now 15%, ok 40%, overstock 25%."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Base seed suffix for reproducibility (default: 42).",
        )

    def handle(self, *args, **options):
        seed_suffix = options["seed"]
        self.stdout.write(f"Seeding stock levels with deterministic RNGs (suffix: {seed_suffix})...")

        # 1. Fetch latest completed forecast run if available
        latest_run = (
            ForecastRun.objects.filter(status="done")
            .order_by("-finished_at", "-created_at")
            .first()
        )

        results_by_series: Dict[tuple, List[Dict[str, Any]]] = {}
        if latest_run:
            results_qs = ForecastResult.objects.filter(run=latest_run).values(
                "store__code", "product__sku", "date", "forecast", "actual"
            )
            for r in results_qs:
                results_by_series.setdefault((r["store__code"], r["product__sku"]), []).append(r)

        # 2. Historical sales fallback if no run
        mean_sales_map: Dict[tuple, float] = {}
        if not latest_run:
            sales_qs = Sale.objects.values("store__code", "product__sku", "date", "units_sold")
            sales_list = list(sales_qs)
            if sales_list:
                df = pd.DataFrame(sales_list)
                df = df.sort_values(by=["store__code", "product__sku", "date"])
                last_28_df = df.groupby(["store__code", "product__sku"]).tail(28)
                mean_series = last_28_df.groupby(["store__code", "product__sku"])["units_sold"].mean()
                mean_sales_map = mean_series.to_dict()

        stores = list(Store.objects.order_by("code"))
        products = list(Product.objects.order_by("sku"))
        lead_time_options = [3, 5, 7, 10]

        created_count = 0
        updated_count = 0

        status_counts: Dict[str, int] = {}
        store_statuses: Dict[str, set] = {s.code: set() for s in stores}

        with transaction.atomic():
            for store in stores:
                for product in products:
                    # Independent deterministic RNG per series
                    rng = random.Random(f"{store.code}:{product.sku}:{seed_suffix}")
                    lead_time_days = rng.choice(lead_time_options)
                    service_level = 0.95

                    # Compute LTD, ROP, SS, avg_daily
                    series_rows = results_by_series.get((store.code, product.sku), [])
                    if series_rows:
                        test_rows = [r for r in series_rows if r["actual"] is not None]
                        future_rows = [r for r in series_rows if r["actual"] is None]
                        future_rows.sort(key=lambda x: x["date"])

                        diffs = [r["actual"] - r["forecast"] for r in test_rows]
                        sigma_daily = (
                            float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 10.0
                        )

                        future_forecasts = [r["forecast"] for r in future_rows]
                        lead_time_demand = float(sum(future_forecasts[:lead_time_days]))
                        avg_daily_forecast = (
                            float(sum(future_forecasts) / len(future_forecasts))
                            if future_forecasts
                            else 50.0
                        )
                    else:
                        mean_sales = float(mean_sales_map.get((store.code, product.sku), 50.0))
                        sigma_daily = max(5.0, 0.25 * mean_sales)
                        lead_time_demand = float(lead_time_days * mean_sales)
                        avg_daily_forecast = mean_sales

                    ss = safety_stock(sigma_daily, lead_time_days, service_level)
                    rop = reorder_point(lead_time_demand, ss)

                    # Scenario distribution:
                    # 20% stockout_risk, 15% reorder_now, 40% ok, 25% overstock
                    u = rng.random()
                    if u < 0.20:
                        # stockout_risk: on_hand < lead_time_demand
                        on_hand = round(lead_time_demand * rng.uniform(0.1, 0.85), 1)
                    elif u < 0.35:
                        # reorder_now: lead_time_demand <= on_hand <= rop
                        spread = max(5.0, rop - lead_time_demand)
                        on_hand = round(lead_time_demand + rng.uniform(0.05, 0.95) * spread, 1)
                        if on_hand > rop:
                            on_hand = round(rop - 0.5, 1)
                        if on_hand < lead_time_demand:
                            on_hand = round(lead_time_demand + 0.5, 1)
                    elif u < 0.75:
                        # ok: rop < on_hand <= 21 * avg_daily_forecast
                        min_ok = rop + 5.0
                        max_ok = max(min_ok + 10.0, 20.0 * avg_daily_forecast)
                        on_hand = round(rng.uniform(min_ok, max_ok), 1)
                        if on_hand / avg_daily_forecast > 21.0:
                            on_hand = round(20.0 * avg_daily_forecast, 1)
                    else:
                        # overstock: on_hand > 21 * avg_daily_forecast
                        on_hand = round(avg_daily_forecast * rng.uniform(22.0, 35.0), 1)

                    on_hand = max(0.0, on_hand)

                    # Track verified classification
                    actual_status = classify(
                        on_hand, lead_time_demand, rop, avg_daily_forecast, overstock_days=21
                    )
                    status_counts[actual_status] = status_counts.get(actual_status, 0) + 1
                    store_statuses[store.code].add(actual_status)

                    _, created = StockLevel.objects.update_or_create(
                        store=store,
                        product=product,
                        defaults={
                            "on_hand": on_hand,
                            "lead_time_days": lead_time_days,
                            "service_level": service_level,
                        },
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded stock levels: {created_count} created, {updated_count} updated."
            )
        )
        self.stdout.write(f"Status distribution: {status_counts}")
        self.stdout.write("Distinct statuses per store:")
        for sc in sorted(store_statuses.keys()):
            self.stdout.write(f"  {sc}: {sorted(store_statuses[sc])}")
