"""Tests for retail endpoints: stores and products."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from apps.retail.models import Product, Store


@pytest.mark.django_db
class TestRetailEndpoints:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="retailuser@shelfwise.app",
            email="retailuser@shelfwise.app",
            password="TestPassword@123",
        )

    def test_stores_unauthenticated(self):
        """GET /api/retail/stores/ requires authentication."""
        resp = self.client.get("/api/retail/stores/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_stores_authenticated(self):
        """GET /api/retail/stores/ returns list of stores with code and name."""
        Store.objects.create(code="S1097", name="Downtown Flagship")
        Store.objects.create(code="S262", name="Westside Outlet")

        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/retail/stores/")
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        assert len(data) == 2
        # Verify ordering and fields
        assert data[0]["code"] == "S1097"
        assert data[0]["name"] == "Downtown Flagship"
        assert "code" in data[0]
        assert "name" in data[0]
        assert data[1]["code"] == "S262"
        assert data[1]["name"] == "Westside Outlet"

    def test_products_unauthenticated(self):
        """GET /api/retail/products/ requires authentication."""
        resp = self.client.get("/api/retail/products/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_products_authenticated(self):
        """GET /api/retail/products/ returns list of products with sku, name, and category."""
        Product.objects.create(sku="P1", name="Organic Milk 1L", category="Dairy")
        Product.objects.create(sku="P2", name="Artisan Sourdough", category="Bakery")

        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/retail/products/")
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        assert len(data) == 2
        assert data[0]["sku"] == "P1"
        assert data[0]["name"] == "Organic Milk 1L"
        assert data[0]["category"] == "Dairy"
        assert data[1]["sku"] == "P2"
        assert data[1]["name"] == "Artisan Sourdough"
        assert data[1]["category"] == "Bakery"
