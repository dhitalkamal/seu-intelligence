"""Create analytics_events and event_health_scores tables."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial intelligence tables with composite indexes."""

    dependencies = [
        ("intelligence", "0000_create_intelligence_schema"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyticsEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("event_id", models.UUIDField(blank=True, null=True)),
                ("organization_id", models.UUIDField(blank=True, null=True)),
                ("user_id", models.UUIDField(blank=True, null=True)),
                ("event_type", models.CharField(max_length=50)),
                (
                    "value",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                ("payload", models.JSONField(default=dict)),
                ("source_service", models.CharField(max_length=50)),
                ("occurred_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": '"intelligence"."analytics_event"'},
        ),
        migrations.AddIndex(
            model_name="analyticsevent",
            index=models.Index(
                fields=["event_id", "event_type", "-occurred_at"],
                name="idx_analytics_event_event",
            ),
        ),
        migrations.AddIndex(
            model_name="analyticsevent",
            index=models.Index(
                fields=["organization_id", "-occurred_at"],
                name="idx_analytics_org",
            ),
        ),
        migrations.CreateModel(
            name="EventHealthScore",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("event_id", models.UUIDField()),
                ("score", models.SmallIntegerField()),
                ("level", models.CharField(max_length=20)),
                (
                    "registration_velocity",
                    models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5),
                ),
                (
                    "conversion_rate",
                    models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5),
                ),
                (
                    "revenue_progress",
                    models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5),
                ),
                ("predicted_attendance", models.IntegerField(default=0)),
                ("risk_flags", models.JSONField(default=list)),
                ("recommendations", models.JSONField(default=list)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": '"intelligence"."event_health_score"'},
        ),
    ]
