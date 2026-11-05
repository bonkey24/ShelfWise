"""Tests for inventory app models, endpoints, services, and management command."""

from datetime import date, timedelta
import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.forecasts.models import ForecastResult, ForecastRun
from apps.inventory.models import StockLevel
from apps.retail.models import Product, Sale, Store


@pytest.mark.django_db
class TestStockLevelModel:
    def test_stock_level_creation_and_defaults(self):
        """Create StockLevel and verify field values and defaults."""
        store = Store.objects.create(code="S_INV_1", name="Inventory Store 1")
        prod = Product.objects.create(sku="P_INV_1", name="Inventory Product 1")

        stock = StockLevel.objects.create(
            store=store,
            product=prod,
            on_hand=150.0,
        )

        assert stock.id is not None
        assert stock.store == store
        assert stock.product == prod
        assert stock.on_hand == 150.0
        assert stock.lead_time_days == 7
        assert stock.service_level == 0.95
        assert stock.updated_at is not None
        assert "S_INV_1 | P_INV_1" in str(stock)

    def test_stock_level_unique_together_constraint(self):
        """Ensure duplicate (store, product) raises IntegrityError."""
        store = Store.objects.create(code="S_INV_2", name="Inventory Store 2")
        prod = Product.objects.create(sku="P_INV_2", name="Inventory Product 2")

        StockLevel.objects.create(
            store=store,
            product=prod,
            on_hand=50.0,
        )

        with pytest.raises(IntegrityError):
            StockLevel.objects.create(
                store=store,
                product=prod,
                on_hand=100.0,
            )


@pytest.mark.django_db
class TestSeedStockCommand:
    def test_seed_stock_execution_and_idempotency(self):
        """Verify seed_stock command seeds stock and is idempotent."""
        store = Store.objects.create(code="S_SEED", name="Seed Store")
        prod = Product.objects.create(sku="P_SEED", name="Seed Product")

        # Create 35 days of sales history
        base_date = date(2025, 1, 1)
        for i in range(35):
            Sale.objects.create(
                store=store,
                product=prod,
                date=base_date + timedelta(days=i),
                units_sold=10.0,
                price=5.0,
                on_promo=False,
            )

        # Run command first time
        call_command("seed_stock", seed=42)
        stock = StockLevel.objects.get(store=store, product=prod)
        assert stock.on_hand > 0.0
        assert stock.lead_time_days in {3, 5, 7, 10}
        assert stock.service_level == 0.95

        first_on_hand = stock.on_hand

        # Run command second time - must update without duplicate error
        call_command("seed_stock", seed=42)
        stock.refresh_from_db()
        assert stock.on_hand == first_on_hand
        assert StockLevel.objects.filter(store=store, product=prod).count() == 1

    def test_seed_stock_variety_across_series(self):
        """Verify seed_stock generates diverse scenarios and deterministic values."""
        for s_idx in range(5):
            store = Store.objects.create(code=f"S_VAR_{s_idx}")
            for p_idx in range(5):
                prod, _ = Product.objects.get_or_create(sku=f"P_VAR_{p_idx}")
                Sale.objects.create(
                    store=store, product=prod, date=date(2025, 1, 1), units_sold=50.0, price=10.0
                )

        call_command("seed_stock", seed=42)
        assert StockLevel.objects.count() >= 25


@pytest.mark.django_db
class TestInventoryEndpoints:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.client = APIClient()
        user = User.objects.create_user(
            username="inv_test@shelfwise.app",
            email="inv_test@shelfwise.app",
        )
        self.client.force_authenticate(user=user)
        self.store1 = Store.objects.create(code="ST1", name="Store 1")
        self.store2 = Store.objects.create(code="ST2", name="Store 2")
        self.prod1 = Product.objects.create(sku="SKU1", name="Product 1")
        self.prod2 = Product.objects.create(sku="SKU2", name="Product 2")

        # Create a completed ForecastRun
        self.run = ForecastRun.objects.create(
            status="done",
            horizon_days=28,
            metrics={"lightgbm": {"wape": 0.08}},
        )

        # Populate test-window and future forecast results
        base_date = date(2025, 1, 1)
        for d_idx in range(28):
            d_test = base_date + timedelta(days=d_idx)
            d_future = base_date + timedelta(days=28 + d_idx)
            test_actual = 100.0 + (10.0 if d_idx % 2 == 0 else -10.0)

            for st in [self.store1, self.store2]:
                for pr in [self.prod1, self.prod2]:
                    # Test window record (actual is not null)
                    ForecastResult.objects.create(
                        run=self.run,
                        store=st,
                        product=pr,
                        date=d_test,
                        forecast=100.0,
                        lower=80.0,
                        upper=120.0,
                        actual=test_actual,
                    )
                    # Future horizon record (actual is null)
                    ForecastResult.objects.create(
                        run=self.run,
                        store=st,
                        product=pr,
                        date=d_future,
                        forecast=100.0,
                        lower=80.0,
                        upper=120.0,
                        actual=None,
                    )

        # ST1 + SKU1: Very low stock -> stockout_risk
        # avg_daily=100, lead_time=5 -> LTD=500. On-hand=100 < LTD (500)
        self.stock_risk = StockLevel.objects.create(
            store=self.store1,
            product=self.prod1,
            on_hand=100.0,
            lead_time_days=5,
            service_level=0.95,
        )

        # ST1 + SKU2: High stock -> overstock
        # avg_daily=100, On-hand=3000 -> DOC=30 > 21
        self.stock_over = StockLevel.objects.create(
            store=self.store1,
            product=self.prod2,
            on_hand=3000.0,
            lead_time_days=5,
            service_level=0.95,
        )

        # ST2 + SKU1: Normal stock -> ok
        # avg_daily=100, LTD=500, SS~36.8, ROP~536.8. On-hand=1000 -> DOC=10 (<21, >ROP)
        self.stock_ok = StockLevel.objects.create(
            store=self.store2,
            product=self.prod1,
            on_hand=1000.0,
            lead_time_days=5,
            service_level=0.95,
        )

        # ST2 + SKU2: Stock between LTD and ROP -> reorder_now
        # LTD=500, SS~36.8, ROP~536.8. On-hand=520 (<= ROP and >= LTD)
        self.stock_reorder = StockLevel.objects.create(
            store=self.store2,
            product=self.prod2,
            on_hand=520.0,
            lead_time_days=5,
            service_level=0.95,
        )

    def test_get_inventory_alerts_all_and_severity_sorting(self):
        """Verify alerts endpoint returns all required fields and sorts by severity."""
        resp = self.client.get("/api/inventory/alerts/", {"run": self.run.id})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 4

        # Check required fields
        required_fields = {
            "store",
            "sku",
            "on_hand",
            "lead_time_days",
            "avg_daily_forecast",
            "lead_time_demand",
            "safety_stock",
            "reorder_point",
            "days_of_cover",
            "status",
            "suggested_order_qty",
        }
        for item in data:
            assert required_fields.issubset(item.keys())

        # Verify severity sort order: stockout_risk must be first
        statuses = [item["status"] for item in data]
        assert statuses[0] == "stockout_risk"
        assert "reorder_now" in statuses
        assert "overstock" in statuses
        assert "ok" in statuses

    def test_get_inventory_alerts_filtering(self):
        """Verify alerts filtering by status, store, and limit."""
        # Filter by status
        resp_status = self.client.get(
            "/api/inventory/alerts/",
            {"run": self.run.id, "status": "stockout_risk"},
        )
        assert resp_status.status_code == status.HTTP_200_OK
        data_status = resp_status.json()
        assert len(data_status) == 1
        assert data_status[0]["status"] == "stockout_risk"

        # Filter by store
        resp_store = self.client.get(
            "/api/inventory/alerts/",
            {"run": self.run.id, "store": "ST1"},
        )
        assert resp_store.status_code == status.HTTP_200_OK
        data_store = resp_store.json()
        assert len(data_store) == 2
        assert all(item["store"] == "ST1" for item in data_store)

        # Filter by limit
        resp_limit = self.client.get(
            "/api/inventory/alerts/",
            {"run": self.run.id, "limit": 2},
        )
        assert resp_limit.status_code == status.HTTP_200_OK
        assert len(resp_limit.json()) == 2

    def test_get_inventory_summary(self):
        """Verify summary endpoint returns counts, total order units, and overstock units."""
        resp = self.client.get("/api/inventory/summary/", {"run": self.run.id})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data["run_id"] == self.run.id
        assert "counts" in data
        assert data["counts"]["stockout_risk"] >= 1
        assert data["counts"]["reorder_now"] >= 1
        assert data["counts"]["overstock"] >= 1
        assert data["counts"]["ok"] >= 1
        assert data["total_suggested_order_units"] > 0
        assert data["estimated_overstock_units"] > 0

    def test_stock_level_list_and_patch(self):
        """Verify stock listing and PATCH updates on on_hand, lead_time_days, and service_level."""
        # List stock
        resp_list = self.client.get("/api/inventory/stock/")
        assert resp_list.status_code == status.HTTP_200_OK
        assert len(resp_list.json()) == 4

        # PATCH stock level
        patch_url = f"/api/inventory/stock/{self.stock_risk.id}/"
        patch_payload = {
            "on_hand": 850.0,
            "lead_time_days": 10,
            "service_level": 0.98,
        }
        resp_patch = self.client.patch(patch_url, patch_payload, format="json")
        assert resp_patch.status_code == status.HTTP_200_OK
        patched_data = resp_patch.json()
        assert patched_data["on_hand"] == 850.0
        assert patched_data["lead_time_days"] == 10
        assert patched_data["service_level"] == 0.98

        self.stock_risk.refresh_from_db()
        assert self.stock_risk.on_hand == 850.0
        assert self.stock_risk.lead_time_days == 10
        assert self.stock_risk.service_level == 0.98

        # PATCH invalid values
        resp_invalid = self.client.patch(patch_url, {"on_hand": -10.0}, format="json")
        assert resp_invalid.status_code == status.HTTP_400_BAD_REQUEST

        resp_invalid_service = self.client.patch(patch_url, {"service_level": 1.5}, format="json")
        assert resp_invalid_service.status_code == status.HTTP_400_BAD_REQUEST
