"""Use case: send a pre-event introduction to another attendee."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import AttendeeMatchEntity
from apps.intelligence.domain.exceptions import MatchNotFoundError, OptInRequiredError
from apps.intelligence.domain.repositories import (
    IAttendeeMatchRepository,
    IConnectionPrivacyRepository,
)


class SendIntroductionUseCase:
    """Mark two attendees as introduced, requiring both to have opted in."""

    def __init__(
        self,
        match_repo: IAttendeeMatchRepository,
        privacy_repo: IConnectionPrivacyRepository,
    ) -> None:
        self._matches = match_repo
        self._privacy = privacy_repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> AttendeeMatchEntity:
        """
        Validate both users have opted in, find the match record, mark as introduced.

        Raises OptInRequiredError if either user has not opted in.
        Raises MatchNotFoundError if no match exists between the two users.
        """
        # ! both parties must have opted in for privacy compliance
        for uid in (requesting_user_id, target_user_id):
            priv = self._privacy.get_or_create(uid, event_id)
            if not priv.opted_in:
                raise OptInRequiredError(f"User {uid} has not opted in to Who to Meet.")

        match = self._matches.get_pair(event_id, requesting_user_id, target_user_id)
        if match is None:
            raise MatchNotFoundError("No match record found between these two attendees.")

        return self._matches.mark_introduced(match.id)
