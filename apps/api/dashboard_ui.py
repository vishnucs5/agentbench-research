from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="", tags=["dashboard-ui"])


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    html_path = Path(__file__).parent / "templates" / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>Dashboard not found</h1><p>Run: python -m uvicorn apps.api.main:app --reload</p>", status_code=404)


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def serve_app():
    return await serve_dashboard()


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    return await serve_dashboard()
