"""URLs for forecasts app."""

from django.urls import path

from apps.forecasts.views import (
    ForecastResultListView,
    ForecastRunCreateView,
    ForecastRunDetailView,
    ForecastRunListView,
    ForecastRunOverviewView,
)

app_name = "forecasts"

urlpatterns = [
    path("", ForecastRunListView.as_view(), name="run-list"),
    path("run/", ForecastRunCreateView.as_view(), name="run-create"),
    path("<int:id>/", ForecastRunDetailView.as_view(), name="run-detail"),
    path("<int:id>/overview/", ForecastRunOverviewView.as_view(), name="run-overview"),
    path("<int:id>/results/", ForecastResultListView.as_view(), name="result-list"),
]

