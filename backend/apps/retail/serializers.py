"""Serializers for retail app: Store and Product."""

from rest_framework import serializers
from .models import Product, Store


class StoreSerializer(serializers.ModelSerializer):
    """Serializer for Store model."""

    class Meta:
        model = Store
        fields = ["id", "code", "name"]


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "category"]

