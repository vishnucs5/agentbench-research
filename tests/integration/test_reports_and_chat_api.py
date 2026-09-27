from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from packages.domain.database import get_db_session, init_db
from packages.domain.models import (
    Chunk,
    Paper,
    PaperPage,
    PaperStatus,
    PlagiarismCheck,
    PlagiarismCheckStatus,
    Project,
    User,
    UserRole,
)
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
    password = "secret_password_123"
    auth_service = AuthService()
    hashed = auth_service.hash_password(password)
    email = f"report_user_{uuid.uuid4().hex[:8]}@example.com"
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
    user = User(
        email=email,
        email_hash=email_hash,
        hashed_password=hashed,
        display_name="Reports Researcher",
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
async def auth_headers(client, test_user):
    user, password = test_user
    response = await client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_project(db_session, test_user):
    user, _ = test_user
    project = Project(
        owner_id=user.id,
        name="Deep Learning Network Defense",
        domain="cybersecurity",
        retention_days=30,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    yield project
    await db_session.execute(delete(Project).where(Project.id == project.id))
    await db_session.commit()


@pytest.fixture
async def populated_project(db_session, test_project):
    """Project with an ingested paper and chunk."""
    paper = Paper(
        project_id=test_project.id,
        title="Transformer-Based Zero-Day Intrusion Detection",
        authors_json=["A. Rahman", "M. Garcia"],
        year=2024,
        doi="10.1109/TDSC.2024.101112",
        source_url="IEEE TDSC",
        status=PaperStatus.INDEXED,
        sha256=f"hash_{uuid.uuid4().hex}",
        storage_key="papers/test_paper.pdf",
        parser_version="v1",
    )
    db_session.add(paper)
    await db_session.commit()
    await db_session.refresh(paper)

    page = PaperPage(
        paper_id=paper.id,
        page_number=1,
        section_label="Introduction",
        text="Transformer models demonstrate a 98.4% detection rate on modern zero-day network traffic.",
        parser_version="v1",
    )
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)

    chunk = Chunk(
        paper_id=paper.id,
        page_id=page.id,
        text="Transformer models demonstrate a 98.4% detection rate on modern zero-day network traffic with low latency.",
        token_count=18,
        chunk_version="v1",
        metadata_json={"page": 1, "section": "intro"},
    )
    db_session.add(chunk)
    await db_session.commit()
    await db_session.refresh(chunk)

    return test_project


@pytest.mark.asyncio
async def test_openapi_reports_and_chat_registered(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/v1/reports/projects/{project_id}/export" in paths
    assert "/v1/reports/preview" in paths
    assert "/v1/reports/plagiarism/{check_id}/export" in paths
    assert "/v1/projects/{project_id}/chat" in paths


@pytest.mark.asyncio
async def test_reports_preview(client, auth_headers, populated_project):
    for rtype in ["bibtex", "latex", "markdown", "audit"]:
        res = await client.post(
            "/v1/reports/preview",
            headers=auth_headers,
            json={"project_id": str(populated_project.id), "report_type": rtype},
        )
        assert res.status_code == 200, f"Preview failed for {rtype}: {res.text}"
        data = res.json()
        assert data["report_type"] == rtype
        assert len(data["content"]) > 0
        assert data["char_count"] > 0
        assert data["filename"]


@pytest.mark.asyncio
async def test_reports_export_file_and_json(client, auth_headers, populated_project):
    # Test file download
    res_file = await client.get(
        f"/v1/reports/projects/{populated_project.id}/export?type=markdown&format=file",
        headers=auth_headers,
    )
    assert res_file.status_code == 200
    assert "attachment; filename=" in res_file.headers.get("content-disposition", "")
    assert "Research Survey" in res_file.text

    # Test json payload
    res_json = await client.get(
        f"/v1/reports/projects/{populated_project.id}/export?type=bibtex&format=json",
        headers=auth_headers,
    )
    assert res_json.status_code == 200
    json_data = res_json.json()
    assert json_data["report_type"] == "bibtex"
    assert "@article" in json_data["content"] or "@inproceedings" in json_data["content"]
    assert "Rahman" in json_data["content"]


@pytest.mark.asyncio
async def test_chat_with_papers_grounded(client, auth_headers, populated_project):
    payload = {
        "query": "What detection rate do transformer models achieve on zero-day traffic?",
        "top_k": 3,
    }
    res = await client.post(
        f"/v1/projects/{populated_project.id}/chat",
        headers=auth_headers,
        json=payload,
    )
    assert res.status_code == 200, f"Chat failed: {res.text}"
    chat_res = res.json()
    assert chat_res["query"] == payload["query"]
    assert len(chat_res["answer"]) > 0
    assert len(chat_res["citations"]) > 0
    citation = chat_res["citations"][0]
    assert "Transformer-Based Zero-Day Intrusion Detection" in citation["paper_title"]
    assert citation["page"] == 1
    assert "98.4%" in citation["chunk_text"]


@pytest.mark.asyncio
async def test_export_plagiarism_certificate(client, auth_headers, test_user, db_session):
    user, _ = test_user
    check = PlagiarismCheck(
        user_id=user.id,
        source_text_hash="abc123hash",
        source_filename="dissertation_chapter_3.pdf",
        status=PlagiarismCheckStatus.COMPLETED,
        overall_similarity=3.4,
        originality_score=96.6,
        total_matches=2,
        provider_used="internal",
    )
    db_session.add(check)
    await db_session.commit()
    await db_session.refresh(check)

    # HTML format
    res_html = await client.get(
        f"/v1/reports/plagiarism/{check.id}/export?format=html",
        headers=auth_headers,
    )
    assert res_html.status_code == 200
    assert "Certificate of Originality" in res_html.text
    assert "96.6%" in res_html.text
    assert "dissertation_chapter_3.pdf" in res_html.text

    # Markdown format
    res_md = await client.get(
        f"/v1/reports/plagiarism/{check.id}/export?format=md",
        headers=auth_headers,
    )
    assert res_md.status_code == 200
    assert "Originality & Plagiarism Audit Certificate" in res_md.text
    assert "96.6%" in res_md.text

    # JSON format
    res_json = await client.get(
        f"/v1/reports/plagiarism/{check.id}/export?format=json",
        headers=auth_headers,
    )
    assert res_json.status_code == 200
    assert res_json.json()["check_id"] == str(check.id)
