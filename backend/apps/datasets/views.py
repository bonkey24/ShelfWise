"""Views for dataset listing and CSV upload."""

from django.db import transaction
import pandas as pd
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.retail.models import Product, Sale, Store
from .models import Dataset
from .serializers import DatasetSerializer, DatasetUploadSerializer
from .services import ingest_sales_csv
from .validators import validate_sales_dataframe


class DatasetListView(APIView):
    """List all uploaded datasets, newest first."""

    @extend_schema(
        summary="List datasets",
        description="Returns all uploaded datasets ordered by creation date (newest first).",
        responses={200: DatasetSerializer(many=True)},
    )
    def get(self, request):
        datasets = Dataset.objects.all().order_by("-created_at")
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetUploadView(APIView):
    """Handle multipart CSV file upload and sales data ingestion."""

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload sales CSV dataset",
        description=(
            "Upload a sales CSV file containing columns: store, sku, date, units_sold, price, on_promo. "
            "Validates schema via Pandera and imports records into PostgreSQL within an atomic transaction."
        ),
        request=DatasetUploadSerializer,
        responses={
            201: DatasetSerializer,
            400: OpenApiResponse(description="Validation error or import failure"),
        },
    )
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"errors": ["No file provided in the 'file' form field."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = request.data.get("name")
        if not name or not str(name).strip():
            name = uploaded_file.name

        # Create dataset in 'processing' status
        dataset = Dataset.objects.create(
            name=str(name).strip(),
            file=uploaded_file,
            status="processing",
        )

        # Ingest CSV file through shared service
        try:
            dataset, rows_imported = ingest_sales_csv(dataset.file.path, dataset=dataset)
            return Response(
                DatasetSerializer(dataset).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as val_err:
            errors = str(val_err).split("\n")
            return Response(
                {"errors": errors, "dataset": DatasetSerializer(dataset).data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as import_err:
            error_msg = f"Database import error: {import_err}"
            return Response(
                {"errors": [error_msg], "dataset": DatasetSerializer(dataset).data},
                status=status.HTTP_400_BAD_REQUEST,
            )
