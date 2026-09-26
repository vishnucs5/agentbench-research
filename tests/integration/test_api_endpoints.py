from __future__ import annotations

import hashlib
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
    password = "integration_test_password_123"
    auth_service = AuthService()
    hashed = auth_service.hash_password(password)
    email = f"user_{uuid4().hex[:8]}@example.com"
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
    user = User(
        email=email,
        email_hash=email_hash,
        hashed_password=hashed,
        display_name="Integration User",
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
        name="Integration Project",
        domain="security",
        retention_days=30,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    yield project
    await db_session.execute(delete(Project).where(Project.id == project.id))
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


@pytest.mark.integration
class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_openapi_schema_no_leaked_parameters(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema

        leaked_param_names = {
            "session",
            "db",
            "extraction_service",
            "retrieval_service",
            "synthesis_service",
            "verification_service",
            "report_service",
            "eval_service",
        }

        leaks = []
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                for param in operation.get("parameters", []):
                    name = param.get("name")
                    if name in leaked_param_names:
                        leaks.append(f"{method.upper()} {path} -> param '{name}'")

        assert len(leaks) == 0, f"OpenAPI schema contains leaked service parameters: {leaks}"

    @pytest.mark.asyncio
    async def test_ui_routes_accessible_without_auth(self, client):
        ui_routes = ["/", "/dashboard", "/app", "/ui", "/projects", "/trace", "/settings"]
        for route in ui_routes:
            resp = await client.get(route)
            assert resp.status_code == 200, f"Route {route} returned status {resp.status_code}"

    @pytest.mark.asyncio
    async def test_auth_and_project_lifecycle(self, client, auth_headers):
        # Create project via API
        create_resp = await client.post(
            "/v1/projects",
            json={
                "name": "API Created Project",
                "description": "Created during integration testing",
                "domain": "security",
                "retention_days": 60,
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        project_data = create_resp.json()
        project_id = project_data["id"]
        assert project_data["name"] == "API Created Project"

        # Get project
        get_resp = await client.get(f"/v1/projects/{project_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == project_id

        # List projects
        list_resp = await client.get("/v1/projects", headers=auth_headers)
        assert list_resp.status_code == 200
        projects = list_resp.json()
        assert any(p["id"] == project_id for p in projects)

    @pytest.mark.asyncio
    async def test_evaluation_endpoints(self, client, auth_headers):
        # List categories
        cat_resp = await client.get("/v1/evaluation/benchmark/categories", headers=auth_headers)
        assert cat_resp.status_code == 200
        cats = cat_resp.json()
        assert len(cats) > 0

        # List difficulties
        diff_resp = await client.get("/v1/evaluation/benchmark/difficulties", headers=auth_headers)
        assert diff_resp.status_code == 200
        diffs = diff_resp.json()
        assert len(diffs) > 0

        # List runs
        runs_resp = await client.get("/v1/evaluation/runs", headers=auth_headers)
        assert runs_resp.status_code == 200
        assert isinstance(runs_resp.json(), list)

    @pytest.mark.asyncio
    async def test_verification_endpoint(self, client, test_project, auth_headers):
        resp = await client.post(
            f"/v1/projects/{test_project.id}/verification/verify",
            json={
                "draft_text": "The 1D-CNN achieves 98.2% accuracy. In our opinion, this model is fast.",
                "paper_ids": [],
                "strict_mode": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "overall_status" in data
        assert "atomic_claims" in data
        assert len(data["atomic_claims"]) >= 2

    @pytest.mark.asyncio
    async def test_synthesis_endpoint(self, client, test_project, auth_headers):
        resp = await client.post(
            f"/v1/projects/{test_project.id}/synthesis",
            json={
                "project_id": str(test_project.id),
                "paper_ids": [],
                "include_conflicts": True,
                "include_gaps": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "comparison_tables" in data
        assert "conflicts" in data
        assert "gaps" in data
