"""URL routes for the intelligence app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    ConnectionPrivacyView,
    ConnectionsView,
    HealthCheckView,
    HealthScoreView,
    IngestView,
    IntroductionView,
    NLPSearchView,
)

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("analytics/ingest/", IngestView.as_view(), name="analytics-ingest"),
    path("events/<uuid:event_id>/health/", HealthScoreView.as_view(), name="event-health"),
    path("nlp/search/", NLPSearchView.as_view(), name="nlp-search"),
    # Who to Meet endpoints (spec section 9.2)
    path(
        "events/<uuid:event_id>/connections/",
        ConnectionsView.as_view(),
        name="connections",
    ),
    path(
        "events/<uuid:event_id>/connections/<uuid:user_id>/introduce/",
        IntroductionView.as_view(),
        name="connections-introduce",
    ),
    path(
        "events/<uuid:event_id>/connections/settings/",
        ConnectionPrivacyView.as_view(),
        name="connections-settings",
    ),
]
