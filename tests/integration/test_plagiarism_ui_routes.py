from __future__ import annotations

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from packages.domain.database import init_db


@pytest.fixture(scope="session", autouse=True)
async def _init_db():
    await init_db()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.integration
class TestPlagiarismUIRoutes:
    @pytest.mark.asyncio
    async def test_plagiarism_checker_route_serves_spa(self, client):
        """Test that /dashboard/plagiarism-checker serves index.html without auth header."""
        resp = await client.get("/dashboard/plagiarism-checker")
        assert resp.status_code == 200
        assert '<div id="root">' in resp.text or "<!doctype html>" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_plagiarism_checker_alias_serves_spa(self, client):
        """Test that /plagiarism-checker serves index.html without auth header."""
        resp = await client.get("/plagiarism-checker")
        assert resp.status_code == 200
        assert '<div id="root">' in resp.text or "<!doctype html>" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_overview_and_other_ui_routes_remain_functional(self, client):
        """Verify regression safety: all existing UI routes still return 200 OK."""
        routes = ["/", "/dashboard", "/app", "/ui", "/projects", "/trace", "/settings"]
        for route in routes:
            resp = await client.get(route)
            assert resp.status_code == 200, f"Route {route} returned status {resp.status_code}"
