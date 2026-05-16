"""Root URL configuration for the intelligence-service."""
from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.intelligence.presentation.urls")),
]
