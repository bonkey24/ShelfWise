"""URL routes for the inventory management API."""

from django.urls import path

from apps.inventory.views import (
    InventoryAlertsView,
    InventorySummaryView,
    StockLevelDetailView,
    StockLevelListView,
)

app_name = "inventory"

urlpatterns = [
    path("alerts/", InventoryAlertsView.as_view(), name="inventory-alerts"),
    path("summary/", InventorySummaryView.as_view(), name="inventory-summary"),
    path("stock/", StockLevelListView.as_view(), name="stock-list"),
    path("stock/<int:pk>/", StockLevelDetailView.as_view(), name="stock-detail"),
]

