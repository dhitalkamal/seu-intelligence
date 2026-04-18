"""Add report_job table to the intelligence schema."""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("intelligence", "0003_healthping"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("requested_by", models.UUIDField()),
                ("report_type", models.CharField(max_length=50)),
                ("filters", models.JSONField(default=dict)),
                ("format", models.CharField(max_length=10)),
                ("status", models.CharField(default="pending", max_length=20)),
                ("file_url", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": '"intelligence"."report_job"',
                "indexes": [
                    models.Index(fields=["requested_by", "-created_at"], name="idx_report_job_user"),
                ],
            },
        ),
    ]
