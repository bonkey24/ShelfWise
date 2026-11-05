"""Inventory management models tracking store and SKU level stock."""

from django.db import models

from apps.retail.models import Product, Store


class StockLevel(models.Model):
    """Tracks current physical stock on hand and replenishment policy parameters per store/SKU."""

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    on_hand = models.FloatField()
    lead_time_days = models.IntegerField(default=7)
    service_level = models.FloatField(default=0.95)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("store", "product")]
        indexes = [
            models.Index(fields=["store", "product"]),
        ]
        ordering = ["store", "product"]

    def __str__(self) -> str:
        return f"{self.store.code} | {self.product.sku}: on_hand={self.on_hand:.1f}"
