"""Views for forecasting API endpoints."""

import threading
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.datasets.models import Dataset
from apps.forecasts.models import ForecastResult, ForecastRun
from apps.forecasts.serializers import (
    ForecastOverviewSerializer,
    ForecastResultSerializer,
    ForecastRunCreateSerializer,
    ForecastRunSerializer,
)
from apps.forecasts.services import cleanup_stale_runs, run_forecast


class ForecastRunCreateView(APIView):
    """Start a new demand forecasting pipeline run."""

    @extend_schema(
        summary="Start forecast run",
        description="Spawns an asynchronous background thread to train LightGBM and generate demand forecasts.",
        request=ForecastRunCreateSerializer,
        responses={202: ForecastRunSerializer},
    )
    def post(self, request):
        serializer = ForecastRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        horizon_days = serializer.validated_data.get("horizon_days", 28)
        dataset_id = serializer.validated_data.get("dataset_id")

        dataset = None
        if dataset_id:
            dataset = get_object_or_404(Dataset, id=dataset_id)

        # Create the run in 'running' status
        run = ForecastRun.objects.create(
            status="running",
            horizon_days=horizon_days,
            dataset=dataset,
        )

        # Launch background thread
        thread = threading.Thread(
            target=run_forecast,
            args=(run.id,),
            daemon=True,
            name=f"ForecastRunWorker-{run.id}",
        )
        thread.start()

        return Response(
            ForecastRunSerializer(run).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ForecastRunListView(APIView):
    """List all forecast runs (newest first)."""

    @extend_schema(
        summary="List forecast runs",
        description="Returns all forecast runs ordered by creation date descending.",
        responses={200: ForecastRunSerializer(many=True)},
    )
    def get(self, request):
        cleanup_stale_runs()
        runs = ForecastRun.objects.all().order_by("-created_at")
        serializer = ForecastRunSerializer(runs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ForecastRunDetailView(APIView):
    """Retrieve status, evaluation metrics, and metadata for a specific forecast run."""

    @extend_schema(
        summary="Get forecast run status and metrics",
        description="Returns status ('pending', 'running', 'done', 'failed'), evaluation metrics, and error info.",
        responses={200: ForecastRunSerializer},
    )
    def get(self, request, id: int):
        cleanup_stale_runs()
        run = get_object_or_404(ForecastRun, id=id)
        serializer = ForecastRunSerializer(run)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ForecastResultListView(APIView):
    """Retrieve forecast results, intervals, and test-window actuals for a run."""

    @extend_schema(
        summary="Get forecast results for a run",
        description="Returns forecast points, lower/upper intervals, and test-window actuals, filterable by store and sku.",
        parameters=[
            OpenApiParameter(name="store", description="Store code to filter by (e.g. 'S1097')", required=False, type=str),
            OpenApiParameter(name="sku", description="Product SKU to filter by (e.g. 'P1')", required=False, type=str),
        ],
        responses={200: ForecastResultSerializer(many=True)},
    )
    def get(self, request, id: int):
        run = get_object_or_404(ForecastRun, id=id)
        queryset = ForecastResult.objects.filter(run=run).select_related("store", "product")

        store_code = request.query_params.get("store")
        sku_code = request.query_params.get("sku")

        if store_code:
            queryset = queryset.filter(store__code=store_code)
        if sku_code:
            queryset = queryset.filter(product__sku=sku_code)

        queryset = queryset.order_by("date", "store__code", "product__sku")
        serializer = ForecastResultSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ForecastRunOverviewView(APIView):
    """Retrieve portfolio-level daily actuals vs forecast aggregated across all stores and SKUs."""

    @extend_schema(
        summary="Get forecast run overview aggregated time series",
        description="Returns model metrics, total daily actual and forecast summed across all series, and dates.",
        responses={200: ForecastOverviewSerializer},
    )
    def get(self, request, id: int):
        from django.db.models import Count, Sum

        cleanup_stale_runs()
        run = get_object_or_404(ForecastRun, id=id)

        qs = (
            ForecastResult.objects.filter(run=run)
            .values("date")
            .annotate(
                total_forecast=Sum("forecast"),
                total_actual=Sum("actual"),
                count_actual=Count("actual"),
            )
            .order_by("date")
        )

        total_daily = []
        dates = []
        first_future_date = None

        for item in qs:
            d_str = (
                item["date"].isoformat()
                if hasattr(item["date"], "isoformat")
                else str(item["date"])
            )
            dates.append(d_str)

            if item["count_actual"] == 0:
                act = None
                if first_future_date is None:
                    first_future_date = d_str
            else:
                act = (
                    round(float(item["total_actual"]), 1)
                    if item["total_actual"] is not None
                    else None
                )

            total_daily.append(
                {
                    "date": d_str,
                    "forecast": (
                        round(float(item["total_forecast"]), 1)
                        if item["total_forecast"] is not None
                        else 0.0
                    ),
                    "actual": act,
                }
            )

        data = {
            "run_id": run.id,
            "status": run.status,
            "metrics": run.metrics or {},
            "first_future_date": first_future_date,
            "total_daily": total_daily,
            "dates": dates,
        }
        return Response(data, status=status.HTTP_200_OK)
