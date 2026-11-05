"""API views for the inventory management module."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.forecasts.models import ForecastRun
from apps.inventory.models import StockLevel
from apps.inventory.serializers import (
    InventoryAlertSerializer,
    InventorySummarySerializer,
    StockLevelSerializer,
    StockLevelUpdateSerializer,
)
from apps.inventory.services import (
    compute_inventory_alerts,
    compute_inventory_summary,
    get_forecast_run,
)


class InventoryAlertsView(APIView):
    """Retrieve store/SKU inventory risk alerts and replenishment metrics."""

    @extend_schema(
        summary="Inventory alerts",
        description=(
            "Calculates inventory risks (stockout_risk, reorder_now, overstock, ok) "
            "and replenishment recommendations for a forecast run. Defaults to the latest completed run."
        ),
        parameters=[
            OpenApiParameter(
                name="run",
                type=int,
                required=False,
                description="Forecast run ID (defaults to latest completed run).",
            ),
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                description="Filter by risk status (stockout_risk, reorder_now, overstock, ok).",
            ),
            OpenApiParameter(
                name="store",
                type=str,
                required=False,
                description="Filter by store code (e.g. S1097).",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                description="Limit maximum returned alert records.",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                required=False,
                description="Offset starting index for pagination.",
            ),
        ],
        responses={200: InventoryAlertSerializer(many=True)},
    )
    def get(self, request):
        run_id = request.query_params.get("run")
        status_filter = request.query_params.get("status")
        store_filter = request.query_params.get("store")
        limit_param = request.query_params.get("limit")
        offset_param = request.query_params.get("offset")

        limit = None
        if limit_param:
            try:
                limit = int(limit_param)
            except ValueError:
                return Response(
                    {"detail": "Parameter 'limit' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        offset = None
        if offset_param:
            try:
                offset = int(offset_param)
            except ValueError:
                return Response(
                    {"detail": "Parameter 'offset' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            run = get_forecast_run(run_id)
        except (ForecastRun.DoesNotExist, ValueError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        alerts = compute_inventory_alerts(
            run=run,
            status_filter=status_filter,
            store_filter=store_filter,
            limit=limit,
            offset=offset,
        )
        serializer = InventoryAlertSerializer(alerts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventorySummaryView(APIView):
    """Retrieve portfolio-level inventory risk counts and replenishment summary."""

    @extend_schema(
        summary="Inventory summary",
        description="Returns counts per status, total suggested order units, and estimated overstock units.",
        parameters=[
            OpenApiParameter(
                name="run",
                type=int,
                required=False,
                description="Forecast run ID (defaults to latest completed run).",
            ),
        ],
        responses={200: InventorySummarySerializer},
    )
    def get(self, request):
        run_id = request.query_params.get("run")

        try:
            run = get_forecast_run(run_id)
        except (ForecastRun.DoesNotExist, ValueError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        summary_data = compute_inventory_summary(run=run)
        serializer = InventorySummarySerializer(summary_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockLevelListView(APIView):
    """List stock levels across all stores and products."""

    @extend_schema(
        summary="List stock levels",
        description="Retrieve on-hand stock and replenishment policy parameters for each store/SKU.",
        parameters=[
            OpenApiParameter(
                name="store",
                type=str,
                required=False,
                description="Filter by store code.",
            ),
            OpenApiParameter(
                name="sku",
                type=str,
                required=False,
                description="Filter by product SKU.",
            ),
        ],
        responses={200: StockLevelSerializer(many=True)},
    )
    def get(self, request):
        qs = StockLevel.objects.select_related("store", "product").all()

        store = request.query_params.get("store")
        if store:
            qs = qs.filter(store__code=store)

        sku = request.query_params.get("sku")
        if sku:
            qs = qs.filter(product__sku=sku)

        serializer = StockLevelSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockLevelDetailView(APIView):
    """Retrieve or partially update a specific StockLevel instance."""

    @extend_schema(
        summary="Retrieve stock level",
        responses={200: StockLevelSerializer},
    )
    def get(self, request, pk: int):
        stock = get_object_or_404(
            StockLevel.objects.select_related("store", "product"),
            pk=pk,
        )
        return Response(StockLevelSerializer(stock).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update stock level",
        description="Partially update on_hand, lead_time_days, or service_level.",
        request=StockLevelUpdateSerializer,
        responses={200: StockLevelSerializer},
    )
    def patch(self, request, pk: int):
        stock = get_object_or_404(
            StockLevel.objects.select_related("store", "product"),
            pk=pk,
        )
        serializer = StockLevelUpdateSerializer(stock, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StockLevelSerializer(stock).data, status=status.HTTP_200_OK)
