"""Serializers for forecast runs and prediction results."""

from rest_framework import serializers

from apps.forecasts.models import ForecastResult, ForecastRun


class ForecastRunCreateSerializer(serializers.Serializer):
    """Input serializer for starting a new forecast run."""

    horizon_days = serializers.IntegerField(default=28, required=False, min_value=1)
    dataset_id = serializers.IntegerField(required=False, allow_null=True)


class ForecastRunSerializer(serializers.ModelSerializer):
    """Serializer for ForecastRun instances."""

    class Meta:
        model = ForecastRun
        fields = [
            "id",
            "dataset",
            "status",
            "horizon_days",
            "metrics",
            "error",
            "created_at",
            "finished_at",
        ]
        read_only_fields = fields


class ForecastResultSerializer(serializers.ModelSerializer):
    """Serializer for individual ForecastResult time series data points."""

    store = serializers.CharField(source="store.code", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = ForecastResult
        fields = [
            "id",
            "date",
            "store",
            "sku",
            "forecast",
            "lower",
            "upper",
            "actual",
        ]
        read_only_fields = fields


class DailyPointSerializer(serializers.Serializer):
    """Aggregated daily demand forecast and actual point."""

    date = serializers.CharField()
    forecast = serializers.FloatField()
    actual = serializers.FloatField(allow_null=True)


class ForecastOverviewSerializer(serializers.Serializer):
    """Overview containing metrics, dates, and total aggregated daily actuals and forecasts."""

    run_id = serializers.IntegerField()
    status = serializers.CharField()
    metrics = serializers.DictField(allow_null=True, required=False)
    first_future_date = serializers.CharField(allow_null=True, required=False)
    total_daily = DailyPointSerializer(many=True)
    dates = serializers.ListField(child=serializers.CharField())

