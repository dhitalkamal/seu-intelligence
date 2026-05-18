"""Use case: update a user's Who to Meet opt-in preference."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import ConnectionPrivacyEntity
from apps.intelligence.domain.repositories import IConnectionPrivacyRepository


class UpdatePrivacyUseCase:
    """Set a user's opted_in preference for the Who to Meet feature at an event."""

    def __init__(self, privacy_repo: IConnectionPrivacyRepository) -> None:
        self._privacy = privacy_repo

    def execute(
        self, *, user_id: uuid.UUID, event_id: uuid.UUID, opted_in: bool
    ) -> ConnectionPrivacyEntity:
        """Upsert the preference and return the updated entity."""
        pref = self._privacy.get_or_create(user_id, event_id)
        pref.opted_in = opted_in
        return self._privacy.upsert(pref)
