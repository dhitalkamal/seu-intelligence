"""Django admin registrations for intelligence domain models."""

from __future__ import annotations

from django.contrib import admin

from apps.intelligence.infrastructure.models import AnalyticsEvent, EventHealthScore

admin.site.register(AnalyticsEvent)
admin.site.register(EventHealthScore)
