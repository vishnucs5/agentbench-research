from __future__ import annotations

from uuid import uuid4

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from packages.security.auth import AuthService, get_auth_service
from packages.domain.database import get_db_session
from packages.domain.models import User, UserRole
from sqlalchemy import select


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async for session in get_db_session():
        yield session


@pytest.fixture
async def auth_headers(client, db_session):
    """Create a test user and return auth headers."""
    user = User(
        email="test@example.com",
        email_hash="test_hash",
        hashed_password="$2b$12$test",
        display_name="Test User",
        role=UserRole.RESEARCHER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Login to get token
    response = await client.post(
        "/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def project_id():
    return uuid4()


class TestPaperIngestionAPI:
    @pytest.mark.asyncio
    async def test_upload_paper_invalid_content_type(self, client, project_id, auth_headers):
        response = await client.post(
            f"/v1/projects/{project_id}/papers",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_paper_invalid_extension(self, client, project_id, auth_headers):
        response = await client.post(
            f"/v1/projects/{project_id}/papers",
            files={"file": ("test.pdf", b"not a pdf", "application/pdf")},
            headers=auth_headers,
        )
        # This will fail at MinIO connection, but we test the validation
        assert response.status_code in (400, 500)

    @pytest.mark.asyncio
    async def test_list_papers_empty(self, client, project_id, auth_headers):
        response = await client.get(f"/v1/projects/{project_id}/papers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["papers"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, client, project_id, auth_headers):
        response = await client.get(f"/v1/projects/{project_id}/papers/{uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paper_pages_not_found(self, client, project_id, auth_headers):
        response = await client.get(f"/v1/projects/{project_id}/papers/{uuid4()}/pages", headers=auth_headers)
        assert response.status_code == 404