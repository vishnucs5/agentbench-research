from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from packages.cache.memory import MemoryCache
from packages.cache.redis import RedisCache
from packages.dashboard.schemas import (
    DashboardFilters,
    PaginatedRuns,
    ProjectDashboardStats,
    RunTraceResponse,
    TraceFilter,
)
from packages.dashboard.trace_replay import TraceReplayService, get_trace_replay_service
from packages.domain.database import get_db_session
from packages.domain.models import Project, ResearchRun, User
from packages.security.middleware import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> None:
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.owner_id == current_user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )


async def _require_owned_run(
    session: AsyncSession, run_id: UUID, current_user: User
) -> ResearchRun:
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(ResearchRun)
        .join(Project, ResearchRun.project_id == Project.id)
        .options(selectinload(ResearchRun.trace_events))
        .where(
            ResearchRun.id == run_id, Project.owner_id == current_user.id
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


async def get_cache() -> RedisCache | MemoryCache:
    from apps.api.main import cache_client

    return cache_client


@router.get("/projects/{project_id}/stats", response_model=ProjectDashboardStats)
async def get_project_stats(
    project_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
    cache: RedisCache | MemoryCache = Depends(get_cache),
) -> ProjectDashboardStats | None:
    await _require_owned_project(session, project_id, current_user)
    cache_key = f"stats:{project_id}"
    try:
        cached = await cache.get(cache_key)
    except Exception:
        cached = None
    if cached:
        result = ProjectDashboardStats(**cached)
    else:
        try:
            result = await service.get_project_stats(project_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        try:
            await cache.set(cache_key, result.model_dump(), ttl=30)
        except Exception:
            pass

    etag = f'"{hash(str(result.model_dump()))}"'
    if request.headers.get("if-none-match") == etag:
        response.status_code = 304
        return None

    response.headers["Cache-Control"] = "private, max-age=30"
    response.headers["ETag"] = etag
    return result


@router.get("/projects/{project_id}/runs", response_model=PaginatedRuns)
async def list_project_runs(
    project_id: UUID,
    request: Request,
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: list[str] | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    model_profile: list[str] | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
    cache: RedisCache | MemoryCache = Depends(get_cache),
) -> PaginatedRuns | None:
    await _require_owned_project(session, project_id, current_user)
    from datetime import datetime

    cache_key = f"runs:{project_id}:p{page}:s{','.join(status or [])}:m{','.join(model_profile or [])}:{search}:{date_from}:{date_to}"
    try:
        cached = await cache.get(cache_key)
    except Exception:
        cached = None
    if cached:
        result = PaginatedRuns(**cached)
    else:
        filters = DashboardFilters(
            project_ids=[project_id],
            statuses=list(status) if status else None,
            date_from=datetime.fromisoformat(date_from) if date_from else None,
            date_to=datetime.fromisoformat(date_to) if date_to else None,
            model_profiles=model_profile,
            search_query=search,
            page=page,
            page_size=page_size,
        )
        result = await service.list_runs(project_id=project_id, filters=filters)
        try:
            await cache.set(cache_key, result.model_dump(), ttl=15)
        except Exception:
            pass

    etag = f'"{hash(str(result.model_dump()))}"'
    if request.headers.get("if-none-match") == etag:
        response.status_code = 304
        return None

    response.headers["Cache-Control"] = "private, max-age=15"
    response.headers["ETag"] = etag
    response.headers["X-Total-Count"] = str(result.total)
    response.headers["X-Total-Pages"] = str(result.total_pages)
    return result


@router.get("/runs/{run_id}/trace", response_model=RunTraceResponse)
async def get_run_trace(
    run_id: UUID,
    event_types: list[str] | None = Query(None),
    components: list[str] | None = Query(None),
    statuses: list[str] | None = Query(None),
    start_sequence: int | None = Query(None),
    end_sequence: int | None = Query(None),
    include_evidence: bool = Query(True),
    include_redacted: bool = Query(False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
    cache: RedisCache | MemoryCache = Depends(get_cache),
) -> RunTraceResponse | None:
    await _require_owned_run(session, run_id, current_user)
    from packages.dashboard.schemas import EventType

    cache_key = f"trace:{run_id}:et{','.join(event_types or [])}:c{','.join(components or [])}:st{','.join(statuses or [])}:ss{start_sequence}:es{end_sequence}:ev{include_evidence}:r{include_redacted}"
    try:
        cached = await cache.get(cache_key)
    except Exception:
        cached = None
    if cached:
        return RunTraceResponse(**cached)

    trace_filter = TraceFilter(
        event_types=[EventType(e) for e in event_types] if event_types else None,
        components=components,
        statuses=statuses,
        start_sequence=start_sequence,
        end_sequence=end_sequence,
        include_evidence=include_evidence,
        include_redacted=include_redacted,
    )

    trace = await service.get_run_trace(run_id, trace_filter)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    try:
        await cache.set(cache_key, trace.model_dump(), ttl=60)
    except Exception:
        pass
    return trace


@router.get("/projects/{project_id}/comparison", response_model=dict)
async def get_comparison_dashboard(
    project_id: UUID,
    synthesis_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> dict[str, object]:
    await _require_owned_project(session, project_id, current_user)
    if synthesis_id:
        return await service.get_comparison_dashboard(synthesis_id)
    return {"message": "Provide synthesis_id to view comparison"}


@router.get("/projects/{project_id}/gaps")
async def get_gaps_dashboard(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> dict[str, object]:
    await _require_owned_project(session, project_id, current_user)
    gaps = await service.get_gaps_dashboard(project_id)
    return {"gaps": gaps}


@router.get("/projects/{project_id}/conflicts")
async def get_conflicts_dashboard(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> dict[str, object]:
    await _require_owned_project(session, project_id, current_user)
    conflicts = await service.get_conflicts_dashboard(project_id)
    return {"conflicts": conflicts}


@router.get("/evaluation/stats")
async def get_evaluation_stats(
    current_user: User = Depends(get_current_user),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> dict[str, object]:
    return await service.get_evaluation_stats()


@router.get("/runs")
async def list_all_runs(
    project_ids: list[UUID] | None = Query(None),
    status: list[str] | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    model_profile: list[str] | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> object:
    from datetime import datetime

    from packages.dashboard.schemas import DashboardFilters

    if project_ids:
        for pid in project_ids:
            await _require_owned_project(session, pid, current_user)
    filters = DashboardFilters(
        project_ids=project_ids,
        statuses=list(status) if status else None,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        model_profiles=model_profile,
        search_query=search,
        page=page,
        page_size=page_size,
    )
    return await service.list_runs(filters=filters)


@router.get("/runs/{run_id}")
async def get_run_detail(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TraceReplayService = Depends(get_trace_replay_service),
) -> dict[str, object]:
    run = await _require_owned_run(session, run_id, current_user)

    return {
        "run_id": run.id,
        "project_id": run.project_id,
        "user_id": run.user_id,
        "request_text": run.request_text,
        "plan": run.plan_json,
        "status": run.status.value,
        "model_profile": run.model_profile,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error_code": run.error_code,
    }
