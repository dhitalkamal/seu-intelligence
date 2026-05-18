"""Unit tests for the Who to Meet feature."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from apps.intelligence.domain.entities import AttendeeMatchEntity, ConnectionPrivacyEntity
from apps.intelligence.domain.exceptions import MatchNotFoundError, OptInRequiredError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_match(
    event_id: uuid.UUID | None = None,
    user_id_a: uuid.UUID | None = None,
    user_id_b: uuid.UUID | None = None,
    score: str = "0.7500",
) -> AttendeeMatchEntity:
    """Build an AttendeeMatchEntity with sensible defaults."""
    return AttendeeMatchEntity(
        id=uuid.uuid4(),
        event_id=event_id or uuid.uuid4(),
        user_id_a=user_id_a or uuid.uuid4(),
        user_id_b=user_id_b or uuid.uuid4(),
        match_score=Decimal(score),
        is_introduced=False,
        created_at=_now(),
    )


class FakeMatchRepo:
    """In-memory attendee match store."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, AttendeeMatchEntity] = {}
        self._users_by_event: dict[uuid.UUID, list[uuid.UUID]] = {}

    def get_matches_for_user(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AttendeeMatchEntity]:
        return [
            m
            for m in self._store.values()
            if m.event_id == event_id and (m.user_id_a == user_id or m.user_id_b == user_id)
        ]

    def get_pair(
        self, event_id: uuid.UUID, user_id_a: uuid.UUID, user_id_b: uuid.UUID
    ) -> AttendeeMatchEntity | None:
        for m in self._store.values():
            if m.event_id == event_id and (
                (m.user_id_a == user_id_a and m.user_id_b == user_id_b)
                or (m.user_id_a == user_id_b and m.user_id_b == user_id_a)
            ):
                return m
        return None

    def bulk_create(self, entities: list[AttendeeMatchEntity]) -> None:
        for e in entities:
            self._store[e.id] = e

    def mark_introduced(self, match_id: uuid.UUID) -> AttendeeMatchEntity:
        m = self._store.get(match_id)
        if m is None:
            raise MatchNotFoundError("Match not found.")
        m.is_introduced = True
        m.introduced_at = _now()
        return m

    def list_user_ids_for_event(self, event_id: uuid.UUID) -> list[uuid.UUID]:
        return self._users_by_event.get(event_id, [])


class FakePrivacyRepo:
    """In-memory privacy preference store."""

    def __init__(self) -> None:
        self._store: dict[tuple, ConnectionPrivacyEntity] = {}

    def get_or_create(self, user_id: uuid.UUID, event_id: uuid.UUID) -> ConnectionPrivacyEntity:
        key = (user_id, event_id)
        if key not in self._store:
            self._store[key] = ConnectionPrivacyEntity(
                id=uuid.uuid4(),
                user_id=user_id,
                event_id=event_id,
                opted_in=False,
                created_at=_now(),
            )
        return self._store[key]

    def upsert(self, entity: ConnectionPrivacyEntity) -> ConnectionPrivacyEntity:
        self._store[(entity.user_id, entity.event_id)] = entity
        return entity


class FakeAnalyticsQueryRepo:
    """Returns canned event_ids for a user."""

    def __init__(self, user_events: dict[uuid.UUID, list[uuid.UUID]] | None = None) -> None:
        self._data = user_events or {}

    def get_event_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        return self._data.get(user_id, [])


# * tests


def test_get_connections_requires_opt_in():
    """Raises OptInRequiredError when user has not opted in."""
    from apps.intelligence.application.use_cases.get_connections import GetConnectionsUseCase

    user_id = uuid.uuid4()
    event_id = uuid.uuid4()
    uc = GetConnectionsUseCase(FakeMatchRepo(), FakePrivacyRepo(), FakeAnalyticsQueryRepo())
    with pytest.raises(OptInRequiredError):
        uc.execute(event_id=event_id, requesting_user_id=user_id)


def test_get_connections_returns_sorted_matches():
    """Returns matches sorted by match_score descending."""
    from apps.intelligence.application.use_cases.get_connections import GetConnectionsUseCase

    user_id = uuid.uuid4()
    event_id = uuid.uuid4()

    match_repo = FakeMatchRepo()
    privacy_repo = FakePrivacyRepo()
    # opt in the user
    priv = privacy_repo.get_or_create(user_id, event_id)
    priv.opted_in = True
    privacy_repo.upsert(priv)

    m1 = make_match(event_id=event_id, user_id_a=user_id, score="0.9000")
    m2 = make_match(event_id=event_id, user_id_a=user_id, score="0.5000")
    match_repo.bulk_create([m1, m2])

    results = GetConnectionsUseCase(match_repo, privacy_repo, FakeAnalyticsQueryRepo()).execute(
        event_id=event_id, requesting_user_id=user_id
    )
    assert results[0].match_score > results[1].match_score


def test_send_introduction_marks_introduced():
    """SendIntroductionUseCase sets is_introduced=True on the match."""
    from apps.intelligence.application.use_cases.send_introduction import SendIntroductionUseCase

    user_id = uuid.uuid4()
    other_id = uuid.uuid4()
    event_id = uuid.uuid4()

    match_repo = FakeMatchRepo()
    privacy_repo = FakePrivacyRepo()

    for uid in (user_id, other_id):
        p = privacy_repo.get_or_create(uid, event_id)
        p.opted_in = True
        privacy_repo.upsert(p)

    m = make_match(event_id=event_id, user_id_a=user_id, user_id_b=other_id)
    match_repo.bulk_create([m])

    result = SendIntroductionUseCase(match_repo, privacy_repo).execute(
        event_id=event_id, requesting_user_id=user_id, target_user_id=other_id
    )
    assert result.is_introduced is True
    assert result.introduced_at is not None


def test_send_introduction_requires_opt_in_for_target():
    """Raises OptInRequiredError when the target user has not opted in."""
    from apps.intelligence.application.use_cases.send_introduction import SendIntroductionUseCase

    user_id = uuid.uuid4()
    other_id = uuid.uuid4()
    event_id = uuid.uuid4()

    match_repo = FakeMatchRepo()
    privacy_repo = FakePrivacyRepo()
    # only requester opts in
    p = privacy_repo.get_or_create(user_id, event_id)
    p.opted_in = True
    privacy_repo.upsert(p)

    m = make_match(event_id=event_id, user_id_a=user_id, user_id_b=other_id)
    match_repo.bulk_create([m])

    with pytest.raises(OptInRequiredError):
        SendIntroductionUseCase(match_repo, privacy_repo).execute(
            event_id=event_id, requesting_user_id=user_id, target_user_id=other_id
        )


def test_update_privacy_settings_opt_in():
    """UpdatePrivacyUseCase creates opted_in=True preference."""
    from apps.intelligence.application.use_cases.update_privacy import UpdatePrivacyUseCase

    user_id = uuid.uuid4()
    event_id = uuid.uuid4()
    privacy_repo = FakePrivacyRepo()

    result = UpdatePrivacyUseCase(privacy_repo).execute(
        user_id=user_id, event_id=event_id, opted_in=True
    )
    assert result.opted_in is True


def test_get_privacy_settings_returns_default_false():
    """GetPrivacyUseCase returns opted_in=False for a new user."""
    from apps.intelligence.application.use_cases.get_privacy import GetPrivacyUseCase

    user_id = uuid.uuid4()
    event_id = uuid.uuid4()
    result = GetPrivacyUseCase(FakePrivacyRepo()).execute(user_id=user_id, event_id=event_id)
    assert result.opted_in is False
