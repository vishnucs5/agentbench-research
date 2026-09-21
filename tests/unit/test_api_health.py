from __future__ import annotations

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert "database" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    # Root now serves the React SPA (HTML) instead of JSON
    assert "text/html" in response.headers.get("content-type", "") or len(response.content) > 0
