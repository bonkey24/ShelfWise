"""URL configuration for ShelfWise project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI Schema & Swagger Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Authentication API
    path("api/auth/", include("apps.accounts.urls")),
    # Retail API
    path("api/retail/", include("apps.retail.urls")),
    # Datasets API
    path("api/datasets/", include("apps.datasets.urls")),
    # Forecasts API
    path("api/forecasts/", include("apps.forecasts.urls")),
    # Inventory API
    path("api/inventory/", include("apps.inventory.urls")),
    # Assistant API
    path("api/assistant/", include("apps.assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
