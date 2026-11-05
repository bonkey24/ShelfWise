"""Serializers for the inventory management API."""

from rest_framework import serializers

from apps.inventory.models import StockLevel


class StockLevelSerializer(serializers.ModelSerializer):
    """Serializer for displaying stock levels with store and product codes."""

    store = serializers.CharField(source="store.code", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = StockLevel
        fields = [
            "id",
            "store",
            "sku",
            "on_hand",
            "lead_time_days",
            "service_level",
            "updated_at",
        ]
        read_only_fields = ["id", "store", "sku", "updated_at"]


class StockLevelUpdateSerializer(serializers.ModelSerializer):
    """Serializer for partially updating a StockLevel instance (PATCH)."""

    on_hand = serializers.FloatField(required=False, min_value=0.0)
    lead_time_days = serializers.IntegerField(required=False, min_value=1)
    service_level = serializers.FloatField(
        required=False,
        min_value=0.001,
        max_value=0.999,
    )

    class Meta:
        model = StockLevel
        fields = [
            "on_hand",
            "lead_time_days",
            "service_level",
        ]


class InventoryAlertSerializer(serializers.Serializer):
    """Serializer for store/SKU inventory risk and replenishment alerts."""

    stock_id = serializers.IntegerField(required=False)
    store = serializers.CharField()
    sku = serializers.CharField()
    on_hand = serializers.FloatField()
    lead_time_days = serializers.IntegerField()
    avg_daily_forecast = serializers.FloatField()
    lead_time_demand = serializers.FloatField()
    safety_stock = serializers.FloatField()
    reorder_point = serializers.FloatField()
    days_of_cover = serializers.FloatField()
    status = serializers.CharField()
    suggested_order_qty = serializers.FloatField()


class InventorySummarySerializer(serializers.Serializer):
    """Serializer for portfolio-level inventory risk and replenishment summary."""

    run_id = serializers.IntegerField()
    counts = serializers.DictField(child=serializers.IntegerField())
    status_counts = serializers.DictField(child=serializers.IntegerField(), required=False)
    total_suggested_order_units = serializers.FloatField()
    estimated_overstock_units = serializers.FloatField()

