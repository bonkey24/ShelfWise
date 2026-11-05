"""Views for retail domain models (Store, Product)."""

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, Store
from .serializers import ProductSerializer, StoreSerializer


class StoreListView(APIView):
    """List all stores, ordered by store code."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List retail stores",
        description="Returns all registered store locations with code and name.",
        responses={200: StoreSerializer(many=True)},
    )
    def get(self, request):
        stores = Store.objects.all().order_by("code")
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductListView(APIView):
    """List all products, ordered by SKU."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List retail products",
        description="Returns all registered products with SKU, name, and category.",
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request):
        products = Product.objects.all().order_by("sku")
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
