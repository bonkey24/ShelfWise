"""Dataset upload tracking model."""

from django.db import models


class Dataset(models.Model):
    """Tracks a CSV file uploaded by the user for import."""

    name = models.CharField(max_length=200)
    file = models.FileField(upload_to="uploads/")
    rows_imported = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"
