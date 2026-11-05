"""Retail domain models: Store, Product, Sale."""

from django.db import models


class Store(models.Model):
    """A physical or logical retail store location."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return self.code


class Product(models.Model):
    """A SKU-level product sold across stores."""

    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return self.sku


class Sale(models.Model):
    """Daily sales record for a (store, product) pair."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="sales")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    date = models.DateField(db_index=True)
    units_sold = models.FloatField()
    price = models.FloatField(null=True, blank=True)
    on_promo = models.BooleanField(default=False)

    class Meta:
        unique_together = [("store", "product", "date")]
        indexes = [
            models.Index(fields=["store", "product", "date"], name="sale_store_product_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.store_id} | {self.product_id} | {self.date}"
