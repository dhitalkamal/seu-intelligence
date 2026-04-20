"""Django Channels WebSocket consumers for real-time intelligence dashboards."""

from __future__ import annotations


def _format_health_event(pings: list[dict]) -> dict:
    """Build the channel layer message payload for a health ping broadcast."""
    return {"type": "health.update", "data": {"pings": pings}}


class HealthDashboardConsumer:
    """WebSocket consumer that streams live health ping results to the dashboard.

    Clients connect to /ws/health/ and receive a broadcast whenever the
    ping_all_services Celery task stores a new round of results.
    """

    group_name = "health_dashboard"

    # the real implementation uses channels.generic.websocket.AsyncJsonWebsocketConsumer
    # but we guard the import so the module can be imported without channels being
    # configured (e.g. during unit tests that only inspect the class attributes)
    try:
        from channels.generic.websocket import AsyncJsonWebsocketConsumer as _Base

        class _Impl(_Base):
            group_name = "health_dashboard"

            async def connect(self) -> None:
                """Join the broadcast group and accept the connection."""
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.accept()

            async def disconnect(self, close_code: int) -> None:
                """Leave the broadcast group on disconnect."""
                await self.channel_layer.group_discard(self.group_name, self.channel_name)

            async def health_update(self, event: dict) -> None:
                """Forward a broadcast health event to this client."""
                await self.send_json(event["data"])

    except ImportError:
        _Impl = None  # type: ignore[assignment]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    # expose the required methods as class attributes so tests can inspect them
    connect = _Impl.connect if _Impl is not None else None
    disconnect = _Impl.disconnect if _Impl is not None else None
    health_update = _Impl.health_update if _Impl is not None else None


# use the real channels consumer when available; fall back to the stub class
if HealthDashboardConsumer._Impl is not None:
    HealthDashboardConsumer = HealthDashboardConsumer._Impl  # type: ignore[assignment,misc]
    HealthDashboardConsumer.group_name = "health_dashboard"


def broadcast_health_update(pings: list[dict]) -> None:
    """Push a health ping update to all connected dashboard WebSocket clients.

    Called from the ping_all_services Celery task after pings are stored.
    No-ops silently when no channel layer is configured.
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    from asgiref.sync import async_to_sync

    async_to_sync(channel_layer.group_send)(
        "health_dashboard",
        _format_health_event(pings),
    )
