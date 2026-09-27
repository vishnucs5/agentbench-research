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


@router.get("/dashboard", include_in_schema=False)
@router.get("/dashboard/{rest:path}", include_in_schema=False)
async def serve_dashboard(rest: str = ""):
    return await serve_react_app()


@router.get("/app", include_in_schema=False)
@router.get("/app/{rest:path}", include_in_schema=False)
async def serve_app(rest: str = ""):
    return await serve_react_app()


@router.get("/ui", include_in_schema=False)
@router.get("/ui/{rest:path}", include_in_schema=False)
async def serve_ui(rest: str = ""):
    return await serve_react_app()


@router.get("/plagiarism", include_in_schema=False)
@router.get("/plagiarism/{rest:path}", include_in_schema=False)
async def serve_plagiarism(rest: str = ""):
    return await serve_react_app()


@router.get("/dashboard/plagiarism-checker", include_in_schema=False)
@router.get("/plagiarism-checker", include_in_schema=False)
async def serve_plagiarism_checker():
    return await serve_react_app()


@router.get("/reports", include_in_schema=False)
@router.get("/reports/{rest:path}", include_in_schema=False)
async def serve_reports(rest: str = ""):
    return await serve_react_app()


@router.get("/chat", include_in_schema=False)
@router.get("/chat/{rest:path}", include_in_schema=False)
async def serve_chat(rest: str = ""):
    return await serve_react_app()
