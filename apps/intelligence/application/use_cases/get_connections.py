"""Use case: get Who to Meet suggestions for a user at an event."""

from __future__ import annotations

import uuid
from decimal import Decimal

from apps.intelligence.domain.entities import AttendeeMatchEntity
from apps.intelligence.domain.exceptions import OptInRequiredError
from apps.intelligence.domain.repositories import (
    IAnalyticsEventQueryRepository,
    IAttendeeMatchRepository,
    IConnectionPrivacyRepository,
)


class GetConnectionsUseCase:
    """Return ranked Who to Meet suggestions for an opted-in attendee."""

    def __init__(
        self,
        match_repo: IAttendeeMatchRepository,
        privacy_repo: IConnectionPrivacyRepository,
        analytics_repo: IAnalyticsEventQueryRepository,
    ) -> None:
        self._matches = match_repo
        self._privacy = privacy_repo
        self._analytics = analytics_repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[AttendeeMatchEntity]:
        """
        Return up to `limit` match suggestions sorted by score descending.

        Raises OptInRequiredError if the user has not opted in.
        Computes and persists new matches on first call if none exist.
        """
        priv = self._privacy.get_or_create(requesting_user_id, event_id)
        if not priv.opted_in:
            raise OptInRequiredError("You must opt in to see Who to Meet suggestions.")

        existing = self._matches.get_matches_for_user(event_id, requesting_user_id)
        if not existing:
            existing = self._compute_and_store_matches(event_id, requesting_user_id)

        return sorted(existing, key=lambda m: m.match_score, reverse=True)[:limit]

    def _compute_and_store_matches(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AttendeeMatchEntity]:
        """
        Score every opted-in co-attendee using Jaccard similarity on past events.

        The score is: |shared_past_events| / |union_of_past_events|, clamped to [0,1].
        Falls back to a baseline score of 0.1 when one user has no history.
        """
        import uuid as _uuid
        from datetime import datetime, timezone

        other_users = [
            uid for uid in self._matches.list_user_ids_for_event(event_id) if uid != user_id
        ]

        user_events = set(self._analytics.get_event_ids_for_user(user_id))
        new_matches = []

        for other_id in other_users:
            existing = self._matches.get_pair(event_id, user_id, other_id)
            if existing is not None:
                new_matches.append(existing)
                continue

            other_events = set(self._analytics.get_event_ids_for_user(other_id))
            union = user_events | other_events
            if union:
                score = Decimal(len(user_events & other_events)) / Decimal(len(union))
            else:
                score = Decimal("0.1000")

            signals = {
                "shared_events": len(user_events & other_events),
                "user_a_total": len(user_events),
                "user_b_total": len(other_events),
            }
            match = AttendeeMatchEntity(
                id=_uuid.uuid4(),
                event_id=event_id,
                user_id_a=user_id,
                user_id_b=other_id,
                match_score=score.quantize(Decimal("0.0001")),
                match_signals=signals,
                is_introduced=False,
                created_at=datetime.now(timezone.utc),
            )
            new_matches.append(match)

        if new_matches:
            self._matches.bulk_create(
                [
                    m
                    for m in new_matches
                    if not self._matches.get_pair(event_id, user_id, m.user_id_b)
                ]
            )

        return new_matches
