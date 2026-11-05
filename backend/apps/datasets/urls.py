"""URLs for datasets app."""

from django.urls import path
from .views import DatasetListView, DatasetUploadView

app_name = "datasets"

urlpatterns = [
    path("", DatasetListView.as_view(), name="dataset-list"),
    path("upload/", DatasetUploadView.as_view(), name="dataset-upload"),
]

