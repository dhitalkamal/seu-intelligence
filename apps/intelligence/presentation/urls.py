"""URL routes for the intelligence app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    AttendancePredictionView,
    ChatbotView,
    ConnectionPrivacyView,
    ConnectionsView,
    GenerateReportView,
    GrowthAnalyticsView,
    HealthCheckView,
    HealthHistoryLatestView,
    HealthHistoryView,
    HealthScoreView,
    IngestView,
    IntroductionView,
    NLPClassificationView,
    NLPEntityExtractionView,
    NLPKeywordsView,
    NLPLanguageDetectionView,
    NLPModerationView,
    NLPSearchView,
    NLPSentimentView,
    NLPSimilarityView,
    PollReportJobView,
    ReportDownloadView,
    ScheduledReportCreateView,
    ScheduledReportDeactivateView,
    ScheduledReportListView,
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
    # NLP endpoints (F7.3)
    path("nlp/sentiment/analyze", NLPSentimentView.as_view(), name="nlp-sentiment"),
    path("nlp/classification/analyze", NLPClassificationView.as_view(), name="nlp-classification"),
    path("nlp/moderation/analyze", NLPModerationView.as_view(), name="nlp-moderation"),
    path("nlp/entities/extract", NLPEntityExtractionView.as_view(), name="nlp-entities"),
    path("nlp/keywords/extract", NLPKeywordsView.as_view(), name="nlp-keywords"),
    path("nlp/language/detect", NLPLanguageDetectionView.as_view(), name="nlp-language"),
    path("nlp/similarity/score", NLPSimilarityView.as_view(), name="nlp-similarity"),
    path("nlp/chat/", ChatbotView.as_view(), name="nlp-chat"),
    # health ping history (superadmin dashboard)
    path("health-history/", HealthHistoryView.as_view(), name="health-history"),
    path("health-history/latest/", HealthHistoryLatestView.as_view(), name="health-history-latest"),
    # report generation (F8.1)
    path("reports/", GenerateReportView.as_view(), name="report-generate"),
    path("reports/<uuid:job_id>/", PollReportJobView.as_view(), name="report-poll"),
    path("reports/<uuid:job_id>/download/", ReportDownloadView.as_view(), name="report-download"),
    # growth analytics and attendance prediction
    path(
        "events/<uuid:event_id>/analytics/growth/",
        GrowthAnalyticsView.as_view(),
        name="event-growth-analytics",
    ),
    path(
        "events/<uuid:event_id>/analytics/predictions/",
        AttendancePredictionView.as_view(),
        name="event-attendance-prediction",
    ),
    # scheduled reports
    path(
        "events/<uuid:event_id>/reports/schedules/",
        ScheduledReportCreateView.as_view(),
        name="scheduled-report-create",
    ),
    path(
        "events/<uuid:event_id>/reports/schedules/list/",
        ScheduledReportListView.as_view(),
        name="scheduled-report-list",
    ),
    path(
        "reports/schedules/<uuid:schedule_id>/",
        ScheduledReportDeactivateView.as_view(),
        name="scheduled-report-deactivate",
    ),
]
