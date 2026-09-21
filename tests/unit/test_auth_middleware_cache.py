"""Tests for AuthMiddleware user session caching."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from packages.security.middleware import AuthMiddleware


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = True
    user.role = MagicMock()
    user.role.value = "researcher"
    return user


@pytest.fixture
def mock_auth_service():
    service = MagicMock()
    payload = MagicMock()
    payload.user_id = uuid.uuid4()
    service.decode_token.return_value = payload
    return service, payload


class TestAuthMiddlewareCaching:
    def test_caches_user_after_db_lookup(self, mock_user, mock_auth_service):
        auth_service, payload = mock_auth_service
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None

        app = FastAPI()
        app.add_middleware(AuthMiddleware, auth_service=auth_service)

        @app.get("/protected")
        async def protected(request: Request):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)

        with patch("packages.security.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("packages.security.middleware.AuthMiddleware._get_cache", new_callable=AsyncMock, return_value=mock_cache):
                response = client.get(
                    "/protected",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == f"user:{mock_user.id}"
        assert call_args[0][1]["email"] == "test@example.com"
        assert call_args[0][1]["role"] == "researcher"
        assert call_args[0][1]["is_active"] is True
        assert call_args[1]["ttl"] == 300

    def test_uses_cached_user_skips_db(self, mock_user, mock_auth_service):
        auth_service, payload = mock_auth_service
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {
            "id": str(mock_user.id),
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "researcher",
            "is_active": True,
        }

        app = FastAPI()
        app.add_middleware(AuthMiddleware, auth_service=auth_service)

        @app.get("/protected")
        async def protected(request: Request):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)

        with patch("packages.security.middleware.get_session") as mock_get_session:
            with patch("packages.security.middleware.AuthMiddleware._get_cache", new_callable=AsyncMock, return_value=mock_cache):
                response = client.get(
                    "/protected",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        mock_get_session.assert_not_called()

    def test_cache_failure_falls_back_to_db(self, mock_user, mock_auth_service):
        auth_service, payload = mock_auth_service
        mock_cache = AsyncMock()
        mock_cache.get.side_effect = Exception("Redis connection failed")

        app = FastAPI()
        app.add_middleware(AuthMiddleware, auth_service=auth_service)

        @app.get("/protected")
        async def protected(request: Request):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)

        with patch("packages.security.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("packages.security.middleware.AuthMiddleware._get_cache", new_callable=AsyncMock, return_value=mock_cache):
                response = client.get(
                    "/protected",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    def test_cache_set_failure_still_serves(self, mock_user, mock_auth_service):
        auth_service, payload = mock_auth_service
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.side_effect = Exception("Redis write failed")

        app = FastAPI()
        app.add_middleware(AuthMiddleware, auth_service=auth_service)

        @app.get("/protected")
        async def protected(request: Request):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)

        with patch("packages.security.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("packages.security.middleware.AuthMiddleware._get_cache", new_callable=AsyncMock, return_value=mock_cache):
                response = client.get(
                    "/protected",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    def test_inactive_cached_user_rejected(self, mock_auth_service):
        auth_service, payload = mock_auth_service
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {
            "id": str(payload.user_id),
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "researcher",
            "is_active": False,
        }

        app = FastAPI()
        app.add_middleware(AuthMiddleware, auth_service=auth_service)

        @app.get("/protected")
        async def protected(request: Request):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)

        with patch("packages.security.middleware.AuthMiddleware._get_cache", new_callable=AsyncMock, return_value=mock_cache):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert response.status_code == 401
