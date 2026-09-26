from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

templates = Jinja2Templates(directory="apps/api/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/projects", response_class=HTMLResponse)
async def dashboard_projects(request: Request):
    return templates.TemplateResponse("projects.html", {"request": request})


@router.get("/papers", response_class=HTMLResponse)
async def dashboard_papers(request: Request):
    return templates.TemplateResponse("papers.html", {"request": request})


@router.get("/runs", response_class=HTMLResponse)
async def dashboard_runs(request: Request):
    return templates.TemplateResponse("runs.html", {"request": request})


@router.get("/synthesis", response_class=HTMLResponse)
async def dashboard_synthesis(request: Request):
    return templates.TemplateResponse("synthesis.html", {"request": request})


@router.get("/evaluation", response_class=HTMLResponse)
async def dashboard_evaluation(request: Request):
    return templates.TemplateResponse("evaluation.html", {"request": request})


@router.get("/settings", response_class=HTMLResponse)
async def dashboard_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})
