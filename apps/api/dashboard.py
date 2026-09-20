from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from packages.dashboard.schemas import (
    DashboardFilters,
    PaginatedRuns,
    ProjectDashboardStats,
    RunTraceResponse,
    TraceFilter,
)
from packages.dashboard.trace_replay import TraceReplayService, get_trace_replay_service
from packages.domain.database import get_db_session

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/projects/{project_id}/stats", response_model=ProjectDashboardStats)
async def get_project_stats(
    project_id: UUID,
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    return await service.get_project_stats(project_id)


@router.get("/projects/{project_id}/runs", response_model=PaginatedRuns)
async def list_project_runs(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: list[str] | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    model_profile: list[str] | None = Query(None),
    search: str | None = Query(None),
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    from datetime import datetime

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
    return await service.list_runs(project_id=project_id, filters=filters)


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
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    from packages.dashboard.schemas import EventType

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
    return trace


@router.get("/projects/{project_id}/comparison", response_model=dict)
async def get_comparison_dashboard(
    project_id: UUID,
    synthesis_id: UUID | None = Query(None),
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    if synthesis_id:
        return await service.get_comparison_dashboard(synthesis_id)
    return {"message": "Provide synthesis_id to view comparison"}


@router.get("/projects/{project_id}/gaps")
async def get_gaps_dashboard(
    project_id: UUID,
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    gaps = await service.get_gaps_dashboard(project_id)
    return {"gaps": gaps}


@router.get("/projects/{project_id}/conflicts")
async def get_conflicts_dashboard(
    project_id: UUID,
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    conflicts = await service.get_conflicts_dashboard(project_id)
    return {"conflicts": conflicts}


@router.get("/evaluation/stats")
async def get_evaluation_stats(
    service: TraceReplayService = Depends(get_trace_replay_service),
):
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
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    from datetime import datetime

    from packages.dashboard.schemas import DashboardFilters

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
    service: TraceReplayService = Depends(get_trace_replay_service),
):
    from packages.domain.models import ResearchRun
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with get_db_session() as session:
        result = await session.execute(
            select(ResearchRun)
            .options(selectinload(ResearchRun.trace_events))
            .where(ResearchRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

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
