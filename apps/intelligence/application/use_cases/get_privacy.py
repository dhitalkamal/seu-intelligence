"""Use case: get a user's Who to Meet privacy settings for an event."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import ConnectionPrivacyEntity
from apps.intelligence.domain.repositories import IConnectionPrivacyRepository


class GetPrivacyUseCase:
    """Return (or initialise) a user's opt-in preference for an event."""

    def __init__(self, privacy_repo: IConnectionPrivacyRepository) -> None:
        self._privacy = privacy_repo

    def execute(self, *, user_id: uuid.UUID, event_id: uuid.UUID) -> ConnectionPrivacyEntity:
        """Return the privacy record, creating a default opted_in=False one if absent."""
        return self._privacy.get_or_create(user_id, event_id)
