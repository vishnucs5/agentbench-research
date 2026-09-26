from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response

router = APIRouter(prefix="", tags=["dashboard-ui"])

STATIC_DIR = Path(__file__).parent / "static"


@router.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return Response(status_code=204)


@router.get("/", include_in_schema=False)
async def serve_react_app():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(
        content="<h1>React app not built</h1><p>Run: cd apps/web && npm run build</p>",
        status_code=404,
    )


@router.get("/projects", include_in_schema=False)
async def serve_projects():
    return await serve_react_app()


@router.get("/projects/{rest:path}", include_in_schema=False)
async def serve_projects_rest(rest: str):
    return await serve_react_app()


@router.get("/trace", include_in_schema=False)
async def serve_trace():
    return await serve_react_app()


@router.get("/settings", include_in_schema=False)
async def serve_settings():
    return await serve_react_app()


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    html_path = Path(__file__).parent / "templates" / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(
        content="<h1>Dashboard not found</h1><p>Run: python -m uvicorn apps.api.main:app --reload</p>",
        status_code=404,
    )


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def serve_app():
    return await serve_dashboard()


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    return await serve_dashboard()


@router.get("/plagiarism", response_class=HTMLResponse, include_in_schema=False)
async def serve_plagiarism():
    html_path = Path(__file__).parent / "templates" / "plagiarism.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>Plagiarism checker not found</h1>", status_code=404)


@router.get("/dashboard/plagiarism-checker", include_in_schema=False)
@router.get("/plagiarism-checker", include_in_schema=False)
async def serve_plagiarism_checker():
    return await serve_react_app()

