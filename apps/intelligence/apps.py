"""Django app config for the intelligence module."""

from __future__ import annotations

from django.apps import AppConfig


class IntelligenceConfig(AppConfig):
    """Registers the intelligence app with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.intelligence"
    label = "intelligence"
