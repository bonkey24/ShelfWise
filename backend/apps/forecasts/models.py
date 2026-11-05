"""Forecast models for tracking forecast runs and point/interval predictions."""

from django.db import models

from apps.datasets.models import Dataset
from apps.retail.models import Product, Store


class ForecastRun(models.Model):
    """Tracks an end-to-end demand forecasting run and its evaluation metrics."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forecast_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    horizon_days = models.IntegerField(default=28)
    metrics = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ForecastRun #{self.id} ({self.status}, horizon={self.horizon_days}d)"


class ForecastResult(models.Model):
    """Point forecast, prediction intervals, and actuals for a (store, product, date)."""

    run = models.ForeignKey(
        ForecastRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="forecast_results",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="forecast_results",
    )
    date = models.DateField()
    forecast = models.FloatField()
    lower = models.FloatField()
    upper = models.FloatField()
    actual = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "store", "product", "date"]),
        ]
        ordering = ["date", "store", "product"]

    def __str__(self) -> str:
        return (
            f"Result run={self.run_id} store={self.store.code} "
            f"sku={self.product.sku} date={self.date}: {self.forecast:.1f}"
        )
