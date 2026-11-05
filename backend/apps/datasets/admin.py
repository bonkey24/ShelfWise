"""Datasets admin registrations."""

from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "rows_imported", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name",)
