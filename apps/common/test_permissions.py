"""Unit tests for RBAC permission classes in apps.common.permissions."""

from __future__ import annotations

from unittest.mock import MagicMock

# * helpers to build fake request/view objects


def _make_request(
    is_authenticated: bool = True,
    is_staff: bool = False,
    remote_addr: str = "127.0.0.1",
    forwarded_for: str | None = None,
    org_roles: dict[str, str] | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
) -> MagicMock:
    """Build a minimal fake DRF Request for permission tests."""
    request = MagicMock()
    request.user.is_authenticated = is_authenticated
    request.user.is_staff = is_staff
    request.META = {"REMOTE_ADDR": remote_addr}
    if forwarded_for:
        request.META["HTTP_X_FORWARDED_FOR"] = forwarded_for
    request.user.org_roles = org_roles or {}
    # no token by default so _get_org_roles falls back to user.org_roles
    del request.user.token
    request.query_params = query_params or {}
    request.data = data or {}
    return request


def _make_view(kwargs: dict | None = None, org_id: str | None = None) -> MagicMock:
    """Build a minimal fake DRF view."""
    view = MagicMock(spec=[])
    view.kwargs = kwargs or {}
    if org_id is not None:
        view.org_id = org_id
    return view


# * IsSuperAdminFromAllowedIP tests


class TestIsSuperAdminFromAllowedIP:
    """Tests for IsSuperAdminFromAllowedIP."""

    def _perm(self):
        from apps.common.permissions import IsSuperAdminFromAllowedIP

        return IsSuperAdminFromAllowedIP()

    def test_rejects_unauthenticated_user(self):
        """Unauthenticated request must be denied."""
        req = _make_request(is_authenticated=False, is_staff=True)
        assert self._perm().has_permission(req, MagicMock()) is False

    def test_rejects_non_staff_authenticated_user(self):
        """Authenticated non-staff user must be denied."""
        req = _make_request(is_authenticated=True, is_staff=False)
        assert self._perm().has_permission(req, MagicMock()) is False

    def test_allows_staff_when_no_ip_list_configured(self, settings):
        """Staff user is allowed when SUPERADMIN_ALLOWED_IPS is empty."""
        settings.SUPERADMIN_ALLOWED_IPS = []
        req = _make_request(is_authenticated=True, is_staff=True)
        assert self._perm().has_permission(req, MagicMock()) is True

    def test_allows_staff_from_whitelisted_ip(self, settings):
        """Staff user from a whitelisted IP is allowed."""
        settings.SUPERADMIN_ALLOWED_IPS = ["10.0.0.1"]
        req = _make_request(is_authenticated=True, is_staff=True, remote_addr="10.0.0.1")
        assert self._perm().has_permission(req, MagicMock()) is True

    def test_rejects_staff_from_unlisted_ip(self, settings):
        """Staff user from a non-whitelisted IP is denied."""
        settings.SUPERADMIN_ALLOWED_IPS = ["10.0.0.1"]
        req = _make_request(is_authenticated=True, is_staff=True, remote_addr="10.0.0.2")
        assert self._perm().has_permission(req, MagicMock()) is False

    def test_uses_first_forwarded_ip(self, settings):
        """X-Forwarded-For header: leftmost IP is used as client IP."""
        settings.SUPERADMIN_ALLOWED_IPS = ["203.0.113.5"]
        req = _make_request(
            is_authenticated=True,
            is_staff=True,
            forwarded_for="203.0.113.5, 10.0.0.1",
        )
        assert self._perm().has_permission(req, MagicMock()) is True


# * IsOrgRole subclass tests


class TestIsOrgMember:
    """Tests for IsOrgMember (covers IsOrgRole base logic)."""

    def _perm(self):
        from apps.common.permissions import IsOrgMember

        return IsOrgMember()

    def test_denies_when_no_org_id_available(self):
        """Request with no org_id in any source must be denied."""
        req = _make_request(org_roles={"42": "member"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is False

    def test_denies_when_user_has_no_role_for_org(self):
        """User with no role for the requested org is denied."""
        req = _make_request(org_roles={"99": "member"}, query_params={"organisation_id": "42"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is False

    def test_allows_member_role(self):
        """User with member role for the requested org is allowed."""
        req = _make_request(org_roles={"42": "member"}, query_params={"organisation_id": "42"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is True

    def test_allows_admin_role(self):
        """Admin role satisfies IsOrgMember."""
        req = _make_request(org_roles={"42": "admin"}, query_params={"organisation_id": "42"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is True

    def test_allows_owner_role(self):
        """Owner role satisfies IsOrgMember."""
        req = _make_request(org_roles={"42": "owner"}, query_params={"organisation_id": "42"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is True

    def test_org_id_from_view_kwargs(self):
        """org_id resolved from view.kwargs takes precedence."""
        req = _make_request(org_roles={"7": "member"})
        view = _make_view(kwargs={"org_id": "7"})
        assert self._perm().has_permission(req, view) is True

    def test_org_id_from_request_data(self):
        """org_id falls back to request.data when not in params."""
        req = _make_request(org_roles={"5": "manager"}, data={"organisation_id": "5"})
        view = _make_view()
        assert self._perm().has_permission(req, view) is True


class TestIsOrgOwner:
    """Tests for IsOrgOwner (only owner role passes)."""

    def _perm(self):
        from apps.common.permissions import IsOrgOwner

        return IsOrgOwner()

    def test_allows_owner(self):
        """Owner role is allowed."""
        req = _make_request(org_roles={"1": "owner"}, query_params={"organisation_id": "1"})
        assert self._perm().has_permission(req, _make_view()) is True

    def test_rejects_member(self):
        """Member role is rejected by IsOrgOwner."""
        req = _make_request(org_roles={"1": "member"}, query_params={"organisation_id": "1"})
        assert self._perm().has_permission(req, _make_view()) is False


class TestIsOrgAdmin:
    """Tests for IsOrgAdmin (owner and admin pass)."""

    def _perm(self):
        from apps.common.permissions import IsOrgAdmin

        return IsOrgAdmin()

    def test_allows_admin(self):
        """Admin role is allowed."""
        req = _make_request(org_roles={"3": "admin"}, query_params={"organisation_id": "3"})
        assert self._perm().has_permission(req, _make_view()) is True

    def test_rejects_manager(self):
        """Manager role is rejected by IsOrgAdmin."""
        req = _make_request(org_roles={"3": "manager"}, query_params={"organisation_id": "3"})
        assert self._perm().has_permission(req, _make_view()) is False


class TestIsOrgManager:
    """Tests for IsOrgManager (owner, admin, and manager pass)."""

    def _perm(self):
        from apps.common.permissions import IsOrgManager

        return IsOrgManager()

    def test_allows_manager(self):
        """Manager role is allowed."""
        req = _make_request(org_roles={"8": "manager"}, query_params={"organisation_id": "8"})
        assert self._perm().has_permission(req, _make_view()) is True

    def test_rejects_member(self):
        """Member role is rejected by IsOrgManager."""
        req = _make_request(org_roles={"8": "member"}, query_params={"organisation_id": "8"})
        assert self._perm().has_permission(req, _make_view()) is False
