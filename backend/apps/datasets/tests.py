"""Tests for datasets app CSV upload and listing endpoints."""

from io import BytesIO
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.datasets.models import Dataset
from apps.retail.models import Product, Sale, Store


@pytest.fixture
def api_client(db):
    client = APIClient()
    user = User.objects.create_user(
        username="datasets_test@shelfwise.app",
        email="datasets_test@shelfwise.app",
    )
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def valid_csv_file():
    csv_content = (
        "store,sku,date,units_sold,price,on_promo\n"
        "S1,P1,2023-01-01,15,2.99,1\n"
        "S1,P2,2023-01-01,20,1.99,0\n"
        "S2,P1,2023-01-01,35,2.89,1\n"
        "S2,P2,2023-01-01,10,,0\n"
    ).encode("utf-8")
    return SimpleUploadedFile(
        "test_valid.csv", csv_content, content_type="text/csv"
    )


@pytest.fixture
def negative_units_csv_file():
    csv_content = (
        "store,sku,date,units_sold,price,on_promo\n"
        "S1,P1,2023-01-01,-5,2.99,1\n"
        "S1,P2,2023-01-01,20,1.99,0\n"
    ).encode("utf-8")
    return SimpleUploadedFile(
        "test_negative.csv", csv_content, content_type="text/csv"
    )


@pytest.fixture
def missing_column_csv_file():
    csv_content = (
        "store,sku,units_sold,price,on_promo\n"  # missing 'date'
        "S1,P1,15,2.99,1\n"
    ).encode("utf-8")
    return SimpleUploadedFile(
        "test_missing_col.csv", csv_content, content_type="text/csv"
    )


@pytest.fixture
def duplicate_rows_csv_file():
    csv_content = (
        "store,sku,date,units_sold,price,on_promo\n"
        "S1,P1,2023-01-01,15,2.99,1\n"
        "S1,P1,2023-01-01,20,2.99,0\n"  # duplicate store+sku+date
    ).encode("utf-8")
    return SimpleUploadedFile(
        "test_duplicate.csv", csv_content, content_type="text/csv"
    )


@pytest.mark.django_db
class TestDatasetUpload:
    """Test suite for CSV dataset upload endpoint."""

    def test_valid_csv_import_success(self, api_client, valid_csv_file):
        """A valid CSV should import correctly, create Stores, Products, and Sales."""
        url = reverse("datasets:dataset-upload")
        response = api_client.post(
            url,
            {"file": valid_csv_file, "name": "Test Valid Dataset"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "done"
        assert data["rows_imported"] == 4
        assert data["name"] == "Test Valid Dataset"

        # Verify DB records
        assert Dataset.objects.count() == 1
        dataset = Dataset.objects.first()
        assert dataset.status == "done"
        assert dataset.rows_imported == 4
        assert dataset.error == ""

        # Verify Stores and Products
        assert Store.objects.filter(code__in=["S1", "S2"]).count() == 2
        assert Product.objects.filter(sku__in=["P1", "P2"]).count() == 2

        # Verify Sales rows
        assert Sale.objects.count() == 4
        s1_p1_sale = Sale.objects.get(store__code="S1", product__sku="P1", date="2023-01-01")
        assert s1_p1_sale.units_sold == 15.0
        assert s1_p1_sale.price == 2.99
        assert s1_p1_sale.on_promo is True

        # Check nullable price
        s2_p2_sale = Sale.objects.get(store__code="S2", product__sku="P2", date="2023-01-01")
        assert s2_p2_sale.price is None
        assert s2_p2_sale.on_promo is False

    def test_invalid_csv_negative_units_sold_returns_400(
        self, api_client, negative_units_csv_file
    ):
        """CSV with negative units_sold should fail validation and return 400."""
        url = reverse("datasets:dataset-upload")
        response = api_client.post(
            url,
            {"file": negative_units_csv_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "errors" in data
        assert any("units_sold" in err for err in data["errors"])

        # Dataset in DB should be marked failed
        assert Dataset.objects.count() == 1
        dataset = Dataset.objects.first()
        assert dataset.status == "failed"
        assert "units_sold" in dataset.error
        assert dataset.rows_imported == 0

        # No sales should be created
        assert Sale.objects.count() == 0

    def test_invalid_csv_missing_column_returns_400(
        self, api_client, missing_column_csv_file
    ):
        """CSV missing required columns should fail validation and return 400."""
        url = reverse("datasets:dataset-upload")
        response = api_client.post(
            url,
            {"file": missing_column_csv_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "errors" in data
        assert any("Missing required column" in err for err in data["errors"])

        # Dataset in DB should be marked failed
        dataset = Dataset.objects.first()
        assert dataset.status == "failed"
        assert "Missing required column" in dataset.error

    def test_invalid_csv_duplicate_rows_returns_400(
        self, api_client, duplicate_rows_csv_file
    ):
        """CSV with duplicate (store, sku, date) rows should fail validation and return 400."""
        url = reverse("datasets:dataset-upload")
        response = api_client.post(
            url,
            {"file": duplicate_rows_csv_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "errors" in data
        assert any("Duplicate" in err for err in data["errors"])

        dataset = Dataset.objects.first()
        assert dataset.status == "failed"

    def test_list_datasets_ordering(self, api_client):
        """GET /api/datasets/ returns datasets newest first."""
        d1 = Dataset.objects.create(name="Dataset 1", file="test1.csv", status="done")
        d2 = Dataset.objects.create(name="Dataset 2", file="test2.csv", status="processing")

        url = reverse("datasets:dataset-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # d2 is newer than d1
        assert data[0]["id"] == d2.id
        assert data[1]["id"] == d1.id


@pytest.mark.django_db
class TestLoadDemoDataCommand:
    """Tests for the load_demo_data management command."""

    def test_load_demo_data_execution_and_idempotency(self, tmp_path):
        from unittest.mock import patch
        from django.core.management import call_command
        from django.contrib.auth import get_user_model
        from apps.forecasts.models import ForecastRun
        from apps.inventory.models import StockLevel

        User = get_user_model()

        # Create temporary sample CSV
        csv_file = tmp_path / "sample_sales.csv"
        rows = ["store,sku,date,units_sold,price,on_promo"]
        for d in range(1, 10):
            rows.append(f"S1,P1,2023-01-0{d},10,2.50,0")
        csv_file.write_text("\n".join(rows), encoding="utf-8")

        def fake_run_forecast(run_id):
            run = ForecastRun.objects.get(id=run_id)
            run.status = "done"
            run.save(update_fields=["status"])
            return run

        with patch("apps.datasets.management.commands.load_demo_data.run_forecast", side_effect=fake_run_forecast) as mock_fc:
            # 1. First run: imports CSV, creates user, runs forecast, seeds stock
            call_command("load_demo_data", file=str(csv_file))

            assert Sale.objects.count() == 9
            user = User.objects.get(email="demo@shelfwise.app")
            assert user.check_password("Demo@12345")
            assert ForecastRun.objects.filter(status="done").exists()
            assert StockLevel.objects.filter(store__code="S1", product__sku="P1").exists()
            assert mock_fc.call_count == 1

            # 2. Second run: idempotent (does not duplicate sales or runs)
            call_command("load_demo_data", file=str(csv_file))
            assert Sale.objects.count() == 9
            assert User.objects.filter(email="demo@shelfwise.app").count() == 1
            # run_forecast shouldn't be called again because a done run exists
            assert mock_fc.call_count == 1

