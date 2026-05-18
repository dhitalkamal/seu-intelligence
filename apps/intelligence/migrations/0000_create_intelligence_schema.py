"""Create the intelligence PostgreSQL schema before the first table migration."""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    """Ensures the intelligence schema exists before any table is created."""

    dependencies: list = []

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS intelligence;",
            reverse_sql="DROP SCHEMA IF EXISTS intelligence CASCADE;",
        ),
    ]
