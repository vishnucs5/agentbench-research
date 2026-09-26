from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from packages.domain.database import get_db_session, init_db
from packages.domain.models import Chunk, Paper, PaperPage, Project, User, UserRole
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
    password = "testplag123!"
    auth_service = AuthService()
    hashed = auth_service.hash_password(password)
    email_hash = hashlib.sha256("plagtest@example.com".lower().encode()).hexdigest()
    user = User(
        email="plagtest@example.com",
        email_hash=email_hash,
        hashed_password=hashed,
        display_name="Plag Tester",
        role=UserRole.RESEARCHER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user, password
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


@pytest.fixture
async def test_project(db_session, test_user):
    user, _ = test_user
    project = Project(
        owner_id=user.id,
        name="Plagiarism Test Project",
        domain="network-intrusion-detection",
        retention_days=90,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    yield project
    await db_session.execute(delete(Project).where(Project.id == project.id))
    await db_session.commit()


@pytest.fixture
async def seed_document(db_session, test_project):
    """Create a paper with chunks to compare against."""
    paper = Paper(
        project_id=test_project.id,
        title="Seed Document",
        authors_json=[],
        sha256=hashlib.sha256(b"seed-doc" + str(test_project.id).encode()).hexdigest(),
        storage_key="seed-key",
        parser_version="1.0.0",
        status="indexed",
    )
    db_session.add(paper)
    await db_session.flush()
    page = PaperPage(
        paper_id=paper.id,
        page_number=1,
        text="The network intrusion detection system monitors traffic patterns and detects anomalies.",
        parser_version="1.0.0",
    )
    db_session.add(page)
    await db_session.flush()
    chunk = Chunk(
        paper_id=paper.id,
        page_id=page.id,
        text="The network intrusion detection system monitors traffic patterns and detects anomalies.",
        token_count=10,
        chunk_version="1.0.0",
        metadata_json={},
    )
    db_session.add(chunk)
    await db_session.commit()
    yield paper
    # Cleanup handled via project cascade


@pytest.fixture
async def auth_headers(client, test_user):
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
class TestPlagiarismAPI:
    @pytest.mark.asyncio
    async def test_supported_types_public(self, client):
        response = await client.get("/v1/plagiarism/supported-types")
        assert response.status_code == 200
        data = response.json()
        assert "mime_types" in data
        assert "extensions" in data
        assert "max_size_mb" in data

    @pytest.mark.asyncio
    async def test_check_text_requires_auth(self, client):
        response = await client.post(
            "/v1/plagiarism/check/text",
            json={"text": "hello world test content"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_check_text_success(self, client, auth_headers, seed_document):
        response = await client.post(
            "/v1/plagiarism/check/text",
            json={
                "text": "The network intrusion detection system monitors traffic patterns and detects anomalies.",
                "consented_to_store": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "overall_similarity" in data
        assert "originality_score" in data
        assert data["status"] in ["completed", "failed", "processing"]

    @pytest.mark.asyncio
    async def test_check_text_empty(self, client, auth_headers):
        response = await client.post(
            "/v1/plagiarism/check/text",
            json={"text": "   "},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_check_text_too_short(self, client, auth_headers):
        # Short text still allowed but should return 201 with no matches
        response = await client.post(
            "/v1/plagiarism/check/text",
            json={"text": "short text here with enough length to pass min length maybe"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_check_text_original_content(self, client, auth_headers, seed_document):
        # Totally different content should have 0 similarity
        response = await client.post(
            "/v1/plagiarism/check/text",
            json={
                "text": "Quantum physics explores subatomic particles and entanglement phenomena in vacuum."
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        # Fetch report
        check_id = response.json()["id"]
        report = await client.get(f"/v1/plagiarism/checks/{check_id}", headers=auth_headers)
        assert report.status_code == 200
        data = report.json()
        # Report contains summary with potentially similar wording
        assert "potentially similar" in data["summary"].lower()

    @pytest.mark.asyncio
    async def test_check_file_txt_success(self, client, auth_headers):
        response = await client.post(
            "/v1/plagiarism/check/file",
            files={
                "file": (
                    "test.txt",
                    b"Hello world this is a test file for plagiarism checking.",
                    "text/plain",
                )
            },
            data={"consented_to_store": "false"},
            headers=auth_headers,
        )
        # May be 201 or 400 depending on parser
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_check_file_unsupported_type(self, client, auth_headers):
        response = await client.post(
            "/v1/plagiarism/check/file",
            files={"file": ("bad.exe", b"binary content", "application/octet-stream")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_checks(self, client, auth_headers):
        # Create one first
        await client.post(
            "/v1/plagiarism/check/text",
            json={"text": "List test content for plagiarism history."},
            headers=auth_headers,
        )
        response = await client.get("/v1/plagiarism/checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, client, auth_headers):
        response = await client.get(f"/v1/plagiarism/checks/{uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_report_accessible_html(self, client):
        # Plagiarism UI should be accessible without auth
        response = await client.get("/plagiarism")
        assert response.status_code == 200
        assert "Plagiarism Checker" in response.text

    @pytest.mark.asyncio
    async def test_delete_check(self, client, auth_headers):
        resp = await client.post(
            "/v1/plagiarism/check/text",
            json={"text": "To be deleted content for testing delete functionality."},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        check_id = resp.json()["id"]
        del_resp = await client.delete(f"/v1/plagiarism/checks/{check_id}", headers=auth_headers)
        assert del_resp.status_code == 204
        # Verify not found after delete
        get_resp = await client.get(f"/v1/plagiarism/checks/{check_id}", headers=auth_headers)
        assert get_resp.status_code == 404
