"""Django Channels WebSocket URL routing for the intelligence app."""

from __future__ import annotations

from django.urls import path

from apps.intelligence.presentation.consumers import HealthDashboardConsumer

websocket_urlpatterns = [
    path("ws/health/", HealthDashboardConsumer.as_asgi()),
]
