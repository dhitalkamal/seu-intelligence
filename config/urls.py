"""Root URL configuration for the intelligence-service."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/",
        include("apps.intelligence.presentation.urls"),
    ),
    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Use relative URL so the browser resolves it through the correct nginx prefix
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url="../?format=json"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url="../?format=json"), name="redoc"),
]
