"""URL configuration for retail app."""

from django.urls import path
from .views import ProductListView, StoreListView

urlpatterns = [
    path("stores/", StoreListView.as_view(), name="store-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
]

