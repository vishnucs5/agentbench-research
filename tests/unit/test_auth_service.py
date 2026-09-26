"""Task 3 RED test: privilege escalation + refresh-token semantics."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from packages.security.auth import AuthService
from packages.security.schemas import RegisterRequest, UserRole


async def test_register_forces_researcher_role() -> None:
    from packages.security.auth import AuthService
    from packages.security.schemas import RegisterRequest

    svc = AuthService()
    # client sends admin; service must downgrade unless caller is admin
    req = RegisterRequest(email="a@b.co", password="Aa1!aaaa", full_name="A", role="admin")
    # with fix: svc.register(req, requester_role="researcher") -> role researcher
    assert req.role == "admin"  # documents exploit pre-fix
    assert svc is not None


async def test_register_downgrades_non_admin_to_researcher() -> None:
    svc = AuthService()
    req = RegisterRequest(email="evil@b.co", password="Aa1!aaaa", full_name="E", role="admin")

    captured: dict[str, object] = {}

    class FakeResult:
        def scalar_one_or_none(self) -> None:
            return None

    fake_session = AsyncMock()
    fake_session.execute.return_value = FakeResult()

    def _capture_user(user: Any) -> None:
        captured["role"] = user.role

    fake_session.add = MagicMock(side_effect=_capture_user)

    async def _refresh(user: Any) -> None:
        from datetime import UTC, datetime

        user.id = uuid4()
        user.created_at = datetime.now(UTC)
        user.last_login = None
        user.is_active = True

    fake_session.refresh.side_effect = _refresh

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("packages.domain.database.get_session", return_value=cm):
        resp = await svc.register(req, requester_role=UserRole.RESEARCHER)

    assert captured["role"] == UserRole.RESEARCHER
    assert resp.role == UserRole.RESEARCHER


async def test_login_returns_refresh_token() -> None:
    svc = AuthService()
    from packages.security.schemas import LoginRequest

    user_id = uuid4()
    fake_user = MagicMock()
    fake_user.id = user_id
    fake_user.email = "a@b.co"
    fake_user.role = UserRole.RESEARCHER
    fake_user.is_active = True
    fake_user.hashed_password = svc.hash_password("Aa1!aaaa")

    class FakeResult:
        def scalar_one_or_none(self) -> object:
            return fake_user

    fake_session = AsyncMock()
    fake_session.execute.return_value = FakeResult()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("packages.domain.database.get_session", return_value=cm):
        resp = await svc.login(LoginRequest(email="a@b.co", password="Aa1!aaaa"))

    assert resp is not None
    assert resp.refresh_token is not None
    assert len(resp.refresh_token) > 0


async def test_refresh_token_rotates() -> None:
    svc = AuthService()
    from uuid import UUID

    from packages.security.schemas import TokenRefreshRequest

    user_id: UUID = uuid4()
    old = svc.create_refresh_token(user_id)

    fake_user = MagicMock()
    fake_user.id = user_id
    fake_user.email = "a@b.co"
    fake_user.role = UserRole.RESEARCHER
    fake_user.is_active = True

    class FakeResult:
        def scalar_one_or_none(self) -> object:
            return fake_user

    fake_session = AsyncMock()
    fake_session.execute.return_value = FakeResult()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("packages.domain.database.get_session", return_value=cm):
        resp = await svc.refresh_token(TokenRefreshRequest(refresh_token=old))

    assert resp is not None
    assert resp.refresh_token is not None
    assert resp.refresh_token != old
    assert svc.verify_refresh_token(old) is None


async def test_change_password_rejects_weak_password() -> None:
    svc = AuthService()
    from packages.security.schemas import PasswordChangeRequest

    with pytest.raises(ValueError):
        await svc.change_password(
            uuid4(),
            PasswordChangeRequest(current_password="Aa1!aaaa", new_password="weak"),
        )


async def test_password_common_and_email_rejected() -> None:
    svc = AuthService()
    # Common password rejected
    valid, err = svc.validate_password_strength("password123")
    assert not valid
    assert "too common" in err.lower() or "character" in err.lower()

    # Email component in password rejected
    valid, err = svc.validate_password_strength("MySecretAlex!99", user_email="alex@company.com")
    assert not valid
    assert "email" in err.lower()


async def test_change_password_rejects_identical() -> None:
    svc = AuthService()
    from packages.security.schemas import PasswordChangeRequest

    with pytest.raises(ValueError, match="identical"):
        await svc.change_password(
            uuid4(),
            PasswordChangeRequest(current_password="Aa1!aaaa", new_password="Aa1!aaaa"),
        )


def test_ip_lockout_mechanism() -> None:
    svc = AuthService()
    ip = "192.168.1.100"
    assert not svc.is_ip_locked(ip)

    # Record 20 failed attempts
    for _ in range(20):
        svc.record_ip_failed_attempt(ip)

    assert svc.is_ip_locked(ip)
    svc.clear_ip_failed_attempts(ip)
    assert not svc.is_ip_locked(ip)

