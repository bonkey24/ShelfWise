"""Django admin configuration for inventory app."""

from django.contrib import admin

from apps.inventory.models import StockLevel


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "product", "on_hand", "lead_time_days", "service_level", "updated_at")
    list_filter = ("store", "lead_time_days", "service_level")
    search_fields = ("store__code", "product__sku")
    readonly_fields = ("updated_at",)
