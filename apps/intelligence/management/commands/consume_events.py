"""Management command: intelligence service RabbitMQ event consumer."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

_QUEUE = "intelligence.events"
_ROUTING_KEY = "#"


class Command(BaseCommand):
    """
    Listen for all platform events and auto-ingest them as analytics events.

    This consumer is the bridge between the event bus and the analytics
    ingestion pipeline - every domain event becomes an analytics record
    without requiring services to call the intelligence API directly.
    """

    help = "Intelligence service RabbitMQ consumer - auto-ingests domain events."

    def handle(self, *args: object, **options: object) -> None:
        """Connect to RabbitMQ and consume all platform events."""
        import pika

        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.stdout.write("Intelligence consumer started - ingesting all platform events.")
        try:
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange="sansaar", exchange_type="topic", durable=True)
            channel.queue_declare(queue=_QUEUE, durable=True)
            channel.queue_bind(queue=_QUEUE, exchange="sansaar", routing_key=_ROUTING_KEY)
            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=_QUEUE, on_message_callback=self._handle)
            channel.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("Intelligence consumer stopped.")
        except Exception:
            logger.exception("Intelligence consumer error.")

    @staticmethod
    def _handle(channel: object, method: object, props: object, body: bytes) -> None:
        """Ingest the event as an analytics record."""
        import pika.spec

        assert isinstance(method, pika.spec.Basic.Deliver)
        try:
            payload = json.loads(body)
            routing_key: str = method.routing_key

            from apps.intelligence.application.use_cases.ingest_event import IngestEventUseCase
            from apps.intelligence.infrastructure.repositories import DjangoAnalyticsEventRepository

            IngestEventUseCase(DjangoAnalyticsEventRepository()).execute(
                event_type=routing_key,
                source_service=routing_key.split(".")[0],
                occurred_at=datetime.now(timezone.utc),
                event_id=_safe_uuid(payload.get("event_id")),
                organisation_id=_safe_uuid(payload.get("organisation_id")),
                user_id=_safe_uuid(payload.get("user_id")),
                value=None,
                payload=payload,
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.debug("Ingested analytics event: %s", routing_key)
        except Exception:
            logger.exception("Intelligence consumer failed to ingest event.")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _safe_uuid(value: object) -> uuid.UUID | None:
    """Return a UUID from a string, or None if missing/invalid."""
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
