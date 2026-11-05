"""Django admin configuration for forecasts app."""

from django.contrib import admin

from apps.forecasts.models import ForecastResult, ForecastRun


@admin.register(ForecastRun)
class ForecastRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "status", "horizon_days", "created_at", "finished_at")
    list_filter = ("status", "horizon_days", "created_at")
    readonly_fields = ("created_at", "finished_at")


@admin.register(ForecastResult)
class ForecastResultAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "store", "product", "date", "forecast", "lower", "upper", "actual")
    list_filter = ("run", "date", "store")
    search_fields = ("store__code", "product__sku")
