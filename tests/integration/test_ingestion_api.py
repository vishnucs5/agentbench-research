from __future__ import annotations

from uuid import uuid4

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from packages.domain.database import get_db_session, init_db
from packages.domain.models import Project, User, UserRole
from packages.security.auth import AuthService
from sqlalchemy import delete


@pytest.fixture(scope="session", autouse=True)
async def _init_db():
    await init_db()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async for session in get_db_session():
        yield session


@pytest.fixture
async def test_user(db_session):
    """Create a test user with valid bcrypt password and return user + password."""
    password = "testpassword123"
    auth_service = AuthService()
    hashed = auth_service.hash_password(password)
    import hashlib

    email_hash = hashlib.sha256("test@example.com".lower().encode()).hexdigest()
    user = User(
        email="test@example.com",
        email_hash=email_hash,
        hashed_password=hashed,
        display_name="Test User",
        role=UserRole.RESEARCHER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user, password
    # Cleanup
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def test_project(db_session, test_user):
    """Create a test project owned by the test user."""
    user, _ = test_user
    project = Project(
        owner_id=user.id,
        name="Test Project",
        domain="network-intrusion-detection",
        retention_days=90,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    yield project
    # Cleanup
    await db_session.execute(delete(Project).where(Project.id == project.id))
    await db_session.commit()


@pytest.fixture
async def auth_headers(client, test_user):
    """Login and return auth headers."""
    user, password = test_user
    response = await client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.integration
class TestPaperIngestionAPI:
    @pytest.mark.asyncio
    async def test_upload_paper_invalid_content_type(self, client, test_project, auth_headers):
        response = await client.post(
            f"/v1/projects/{test_project.id}/papers",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_paper_invalid_extension(self, client, test_project, auth_headers):
        response = await client.post(
            f"/v1/projects/{test_project.id}/papers",
            files={"file": ("test.txt", b"not a pdf", "application/pdf")},
            headers=auth_headers,
        )
        # Extension validation should reject non-PDF files
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_papers_empty(self, client, test_project, auth_headers):
        response = await client.get(f"/v1/projects/{test_project.id}/papers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["papers"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, client, test_project, auth_headers):
        response = await client.get(
            f"/v1/projects/{test_project.id}/papers/{uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paper_pages_not_found(self, client, test_project, auth_headers):
        response = await client.get(
            f"/v1/projects/{test_project.id}/papers/{uuid4()}/pages", headers=auth_headers
        )
        assert response.status_code == 404
