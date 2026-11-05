"""Tests for forecasts app models and forecasting service."""

from datetime import date, timedelta
import pytest
from django.utils import timezone

from apps.forecasts.models import ForecastResult, ForecastRun
from apps.forecasts.services import run_forecast
from apps.retail.models import Product, Sale, Store


@pytest.mark.django_db
class TestForecastModels:
    def test_forecast_run_lifecycle(self):
        """Verify ForecastRun default values and string representation."""
        run = ForecastRun.objects.create(horizon_days=28)
        assert run.status == "pending"
        assert run.horizon_days == 28
        assert run.metrics == {}
        assert run.error == ""
        assert run.finished_at is None
        assert f"ForecastRun #{run.id}" in str(run)

    def test_forecast_result_creation(self):
        """Verify ForecastResult creation, relations, and fields."""
        run = ForecastRun.objects.create()
        store = Store.objects.create(code="S_TEST_1", name="Store 1")
        prod = Product.objects.create(sku="P_TEST_1", name="Product 1")

        res = ForecastResult.objects.create(
            run=run,
            store=store,
            product=prod,
            date=date(2025, 1, 1),
            forecast=120.5,
            lower=100.0,
            upper=140.0,
            actual=125.0,
        )

        assert res.run == run
        assert res.store == store
        assert res.product == prod
        assert res.forecast == 120.5
        assert res.lower == 100.0
        assert res.upper == 140.0
        assert res.actual == 125.0


@pytest.mark.django_db
class TestForecastService:
    @pytest.fixture
    def populated_sales(self):
        """Create 90 days of daily sales for 2 stores and 2 products (360 Sale rows)."""
        s1 = Store.objects.create(code="S1", name="Store 1")
        s2 = Store.objects.create(code="S2", name="Store 2")
        p1 = Product.objects.create(sku="P1", name="Product 1")
        p2 = Product.objects.create(sku="P2", name="Product 2")

        start_date = date(2024, 1, 1)
        sales = []
        for day in range(90):
            cur_date = start_date + timedelta(days=day)
            on_promo = bool((day // 7) % 2 == 1)  # alternating weekly promo
            for st in [s1, s2]:
                for prod in [p1, p2]:
                    base_sales = 50.0 if st == s1 else 100.0
                    multiplier = 1.3 if on_promo else 1.0
                    units = base_sales * multiplier + (cur_date.weekday() * 5.0)
                    sales.append(
                        Sale(
                            store=st,
                            product=prod,
                            date=cur_date,
                            units_sold=units,
                            price=2.99,
                            on_promo=on_promo,
                        )
                    )
        Sale.objects.bulk_create(sales)
        return s1, s2, p1, p2

    def test_run_forecast_success(self, populated_sales):
        """Test complete run_forecast execution on populated database."""
        run = ForecastRun.objects.create(horizon_days=14)
        completed_run = run_forecast(run.id)

        assert completed_run.status == "done"
        assert completed_run.error == ""
        assert completed_run.finished_at is not None

        # Verify metrics structure
        metrics = completed_run.metrics
        assert "Naive" in metrics
        assert "Seasonal Naive (28d)" in metrics
        assert "LightGBM" in metrics
        for m_name in ["Naive", "Seasonal Naive (28d)", "LightGBM"]:
            assert "WAPE" in metrics[m_name]
            assert "Bias" in metrics[m_name]
            assert "RMSSE" in metrics[m_name]

        # Verify results in database
        results = ForecastResult.objects.filter(run=completed_run)
        assert results.exists()

        # Test window results have actuals filled in
        test_results = results.filter(actual__isnull=False)
        # 14 days * 2 stores * 2 products = 56 test results
        assert test_results.count() == 14 * 2 * 2

        # Future window results have actuals as None
        future_results = results.filter(actual__isnull=True)
        # 14 days * 2 stores * 2 products = 56 future results
        assert future_results.count() == 14 * 2 * 2

        # Check prediction intervals
        for r in results:
            assert r.lower >= 0.0
            assert r.upper >= r.lower
            assert r.forecast >= 0.0

    def test_run_forecast_no_sales_fails_gracefully(self):
        """Verify run_forecast sets status to failed when no sales exist."""
        run = ForecastRun.objects.create(horizon_days=14)

        with pytest.raises(ValueError, match="No sales data available"):
            run_forecast(run.id)

        run.refresh_from_db()
        assert run.status == "failed"
        assert "No sales data available" in run.error
        assert run.finished_at is not None


@pytest.mark.django_db(transaction=True)
class TestForecastAPI:
    """End-to-end integration tests for forecast REST API endpoints."""

    @pytest.fixture
    def client(self):
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient
        c = APIClient()
        user = User.objects.create_user(
            username="forecast_test@shelfwise.app",
            email="forecast_test@shelfwise.app",
        )
        c.force_authenticate(user=user)
        return c

    @pytest.fixture
    def populated_sales(self):
        """Create 90 days of daily sales for 2 stores and 2 products."""
        s1 = Store.objects.create(code="S1", name="Store 1")
        s2 = Store.objects.create(code="S2", name="Store 2")
        p1 = Product.objects.create(sku="P1", name="Product 1")
        p2 = Product.objects.create(sku="P2", name="Product 2")

        start_date = date(2024, 1, 1)
        sales = []
        for day in range(90):
            cur_date = start_date + timedelta(days=day)
            on_promo = bool((day // 7) % 2 == 1)
            for st in [s1, s2]:
                for prod in [p1, p2]:
                    base_sales = 50.0 if st == s1 else 100.0
                    multiplier = 1.3 if on_promo else 1.0
                    units = base_sales * multiplier + (cur_date.weekday() * 5.0)
                    sales.append(
                        Sale(
                            store=st,
                            product=prod,
                            date=cur_date,
                            units_sold=units,
                            price=2.99,
                            on_promo=on_promo,
                        )
                    )
        Sale.objects.bulk_create(sales)
        return s1, s2, p1, p2

    def test_post_run_starts_background_thread(self, client, monkeypatch):
        """POST /api/forecasts/run/ returns 202 and status 'running'."""
        started = []
        monkeypatch.setattr(
            "threading.Thread.start",
            lambda self: started.append(self.name),
        )
        resp = client.post("/api/forecasts/run/", {"horizon_days": 14}, format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "running"
        assert "id" in resp.data
        assert resp.data["horizon_days"] == 14
        assert len(started) == 1

    def test_end_to_end_api_lifecycle(self, client, populated_sales):
        """Full API test: POST run -> wait -> GET detail -> GET list -> GET results."""
        # 1. Start run via API
        post_resp = client.post("/api/forecasts/run/", {"horizon_days": 14}, format="json")
        assert post_resp.status_code == 202
        run_id = post_resp.data["id"]

        # 2. Wait for background thread to complete
        run = ForecastRun.objects.get(id=run_id)
        import time
        max_wait = 15
        waited = 0
        while run.status == "running" and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
            run.refresh_from_db()

        assert run.status == "done", f"Run failed with error: {run.error}"

        # 3. GET /api/forecasts/{id}/ (detail & status & metrics)
        detail_resp = client.get(f"/api/forecasts/{run_id}/")
        assert detail_resp.status_code == 200
        assert detail_resp.data["status"] == "done"
        assert "Naive" in detail_resp.data["metrics"]
        assert "Seasonal Naive (28d)" in detail_resp.data["metrics"]
        assert "LightGBM" in detail_resp.data["metrics"]

        # 4. GET /api/forecasts/ (list)
        list_resp = client.get("/api/forecasts/")
        assert list_resp.status_code == 200
        run_ids = [r["id"] for r in list_resp.data]
        assert run_id in run_ids

        # 5. GET /api/forecasts/{id}/results/?store=S1&sku=P1
        results_resp = client.get(f"/api/forecasts/{run_id}/results/?store=S1&sku=P1")
        assert results_resp.status_code == 200
        results_data = results_resp.data
        # 14 days test + 14 days future = 28 results for this series
        assert len(results_data) == 28

        for row in results_data:
            assert row["store"] == "S1"
            assert row["sku"] == "P1"
            assert "forecast" in row
            assert "lower" in row
            assert "upper" in row

        # Check presence of test-window rows (actual is float) and future rows (actual is None)
        test_rows = [r for r in results_data if r["actual"] is not None]
        future_rows = [r for r in results_data if r["actual"] is None]
        assert len(test_rows) == 14
        assert len(future_rows) == 14

    def test_run_detail_not_found(self, client):
        """GET /api/forecasts/999999/ returns 404."""
        resp = client.get("/api/forecasts/999999/")
        assert resp.status_code == 404

    def test_forecast_overview_endpoint(self, client):
        """GET /api/forecasts/{id}/overview/ returns aggregated metrics, daily totals, and dates."""
        run = ForecastRun.objects.create(
            status="done",
            metrics={"LightGBM": {"WAPE": 0.088}},
        )
        s1 = Store.objects.create(code="S_OV_1")
        s2 = Store.objects.create(code="S_OV_2")
        p1 = Product.objects.create(sku="P_OV_1")

        # Day 1: test window (actual present)
        ForecastResult.objects.create(
            run=run, store=s1, product=p1, date=date(2025, 1, 1), forecast=10.0, actual=12.0, lower=8.0, upper=14.0
        )
        ForecastResult.objects.create(
            run=run, store=s2, product=p1, date=date(2025, 1, 1), forecast=20.0, actual=25.0, lower=15.0, upper=25.0
        )

        # Day 2: future horizon (actual None)
        ForecastResult.objects.create(
            run=run, store=s1, product=p1, date=date(2025, 1, 2), forecast=15.0, actual=None, lower=10.0, upper=20.0
        )
        ForecastResult.objects.create(
            run=run, store=s2, product=p1, date=date(2025, 1, 2), forecast=25.0, actual=None, lower=20.0, upper=30.0
        )

        resp = client.get(f"/api/forecasts/{run.id}/overview/")
        assert resp.status_code == 200
        data = resp.json()

        assert data["run_id"] == run.id
        assert data["status"] == "done"
        assert data["metrics"] == {"LightGBM": {"WAPE": 0.088}}
        assert data["first_future_date"] == "2025-01-02"
        assert data["dates"] == ["2025-01-01", "2025-01-02"]
        assert len(data["total_daily"]) == 2

        # Day 1 total
        assert data["total_daily"][0]["date"] == "2025-01-01"
        assert data["total_daily"][0]["forecast"] == 30.0
        assert data["total_daily"][0]["actual"] == 37.0

        # Day 2 total
        assert data["total_daily"][1]["date"] == "2025-01-02"
        assert data["total_daily"][1]["forecast"] == 40.0
        assert data["total_daily"][1]["actual"] is None

    def test_stale_runs_cleanup(self, client):
        """Forecast runs left in 'running' older than 10 minutes are marked failed with explanation."""
        # 1. Stale run created 15 minutes ago
        stale_run = ForecastRun.objects.create(status="running")
        ForecastRun.objects.filter(id=stale_run.id).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )

        # 2. Fresh run created 2 minutes ago
        fresh_run = ForecastRun.objects.create(status="running")
        ForecastRun.objects.filter(id=fresh_run.id).update(
            created_at=timezone.now() - timedelta(minutes=2)
        )

        # Query detail of stale run
        resp = client.get(f"/api/forecasts/{stale_run.id}/")
        assert resp.status_code == 200
        assert resp.data["status"] == "failed"
        assert resp.data["error"] == "Interrupted (server restart or timeout)"

        # Query detail of fresh run
        fresh_resp = client.get(f"/api/forecasts/{fresh_run.id}/")
        assert fresh_resp.status_code == 200
        assert fresh_resp.data["status"] == "running"
        assert fresh_resp.data["error"] == ""

        # Listing runs also cleans up stale runs
        another_stale = ForecastRun.objects.create(status="running")
        ForecastRun.objects.filter(id=another_stale.id).update(
            created_at=timezone.now() - timedelta(minutes=20)
        )

        list_resp = client.get("/api/forecasts/")
        assert list_resp.status_code == 200
        runs_by_id = {r["id"]: r for r in list_resp.data}
        assert runs_by_id[another_stale.id]["status"] == "failed"
        assert runs_by_id[another_stale.id]["error"] == "Interrupted (server restart or timeout)"


