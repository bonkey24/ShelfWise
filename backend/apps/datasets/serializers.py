"""Serializers for datasets API."""

from rest_framework import serializers
from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model details and listing."""

    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "file",
            "rows_imported",
            "status",
            "error",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "rows_imported",
            "status",
            "error",
            "created_at",
        ]


class DatasetUploadSerializer(serializers.Serializer):
    """Serializer for multipart CSV upload schema."""

    file = serializers.FileField(help_text="CSV file containing sales data")
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional dataset display name",
    )

