"""URL routes for the intelligence app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import HealthCheckView, HealthScoreView, IngestView, NLPSearchView

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("analytics/ingest/", IngestView.as_view(), name="analytics-ingest"),
    path("events/<uuid:event_id>/health/", HealthScoreView.as_view(), name="event-health"),
    path("nlp/search/", NLPSearchView.as_view(), name="nlp-search"),
]
