"""Retail admin registrations."""

from django.contrib import admin
from .models import Product, Sale, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category")
    search_fields = ("sku", "name", "category")
    list_filter = ("category",)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("store", "product", "date", "units_sold", "price", "on_promo")
    list_filter = ("on_promo", "date", "store")
    search_fields = ("store__code", "product__sku")
