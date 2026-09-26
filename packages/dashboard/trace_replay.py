from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from packages.dashboard.schemas import (
    ComparisonDashboardData,
    ConflictDashboardItem,
    DashboardFilters,
    EvaluationDashboardStats,
    GapDashboardItem,
    PaginatedRuns,
    ProjectDashboardStats,
    RunListItem,
    RunTraceResponse,
    TraceEventResponse,
    TraceFilter,
)
from packages.domain.database import get_session
from packages.domain.models import EventType, Paper, Project, ResearchRun, RunStatus, TraceEvent
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class TraceReplayService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_run_trace(
        self, run_id: UUID, trace_filter: TraceFilter | None = None
    ) -> RunTraceResponse | None:
        run = await self._get_run_with_events(run_id)
        if not run:
            return None

        events = list(run.trace_events)

        if trace_filter:
            events = self._apply_trace_filter(events, trace_filter)

        total_latency = sum(e.latency_ms or 0 for e in run.trace_events)
        tool_calls = sum(1 for e in run.trace_events if e.event_type == EventType.TOOL_CALL)
        evidence_ids = list({eid for e in run.trace_events for eid in e.evidence_ids})

        return RunTraceResponse(
            run_id=run.id,
            project_id=run.project_id,
            user_id=run.user_id,
            request_text=run.request_text,
            plan=run.plan_json,
            status=run.status,
            model_profile=run.model_profile,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_code=run.error_code,
            trace_events=[
                TraceEventResponse(
                    event_id=e.id,
                    sequence_no=e.sequence_no,
                    event_type=e.event_type,
                    component=e.component,
                    action=e.action,
                    status=e.status,
                    latency_ms=e.latency_ms,
                    input_summary=e.input_summary,
                    output_summary=e.output_summary,
                    evidence_ids=e.evidence_ids,
                    model_profile=e.model_profile,
                    redaction_version=e.redaction_version,
                    created_at=e.created_at,
                )
                for e in events
            ],
            total_latency_ms=total_latency,
            total_tool_calls=tool_calls,
            budgets=self._extract_budgets(run.plan_json),
            evidence_ids=evidence_ids,
        )

    def _apply_trace_filter(
        self, events: list[TraceEvent], trace_filter: TraceFilter
    ) -> list[TraceEvent]:
        filtered = events

        if trace_filter.event_types:
            filtered = [e for e in filtered if e.event_type in trace_filter.event_types]

        if trace_filter.components:
            filtered = [e for e in filtered if e.component in trace_filter.components]

        if trace_filter.statuses:
            filtered = [e for e in filtered if e.status in trace_filter.statuses]

        if trace_filter.start_sequence is not None:
            filtered = [e for e in filtered if e.sequence_no >= trace_filter.start_sequence]

        if trace_filter.end_sequence is not None:
            filtered = [e for e in filtered if e.sequence_no <= trace_filter.end_sequence]

        return filtered

    def _extract_budgets(self, plan_json: Any) -> dict[str, Any]:
        if isinstance(plan_json, dict):
            return {
                "max_papers": plan_json.get("max_papers"),
                "max_tool_calls": plan_json.get("max_tool_calls"),
                "deadline_seconds": plan_json.get("deadline_seconds"),
                "token_budget": plan_json.get("token_budget"),
            }
        return {
            "max_papers": None,
            "max_tool_calls": None,
            "deadline_seconds": None,
            "token_budget": None,
        }

    async def _get_run_with_events(self, run_id: UUID) -> ResearchRun | None:
        result = await self._session.execute(
            select(ResearchRun)
            .options(selectinload(ResearchRun.trace_events))
            .where(ResearchRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def update_run_status(self, run_id: UUID, status: str) -> None:
        from apps.api.main import app

        ws_manager = app.state.ws_manager

        run = await self._get_run_with_events(run_id)
        if run:
            run.status = status
            await self._session.flush()
            await self._session.commit()

            await ws_manager.broadcast_run_update(
                str(run.project_id),
                {
                    "run_id": str(run_id),
                    "status": status,
                    "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                },
            )
            await ws_manager.broadcast_stats_update(str(run.project_id))

    async def list_runs(
        self,
        project_id: UUID | None = None,
        filters: DashboardFilters | None = None,
    ) -> PaginatedRuns:
        query = select(ResearchRun)

        if project_id:
            query = query.where(ResearchRun.project_id == project_id)

        if filters:
            if filters.project_ids:
                query = query.where(ResearchRun.project_id.in_(filters.project_ids))
            if filters.statuses:
                query = query.where(ResearchRun.status.in_(filters.statuses))
            if filters.date_from:
                query = query.where(ResearchRun.started_at >= filters.date_from)
            if filters.date_to:
                query = query.where(ResearchRun.started_at <= filters.date_to)
            if filters.model_profiles:
                query = query.where(ResearchRun.model_profile.in_(filters.model_profiles))
            if filters.search_query:
                query = query.where(ResearchRun.request_text.ilike(f"%{filters.search_query}%"))

        page = filters.page if filters else 1
        page_size = filters.page_size if filters else 20

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(ResearchRun.started_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(query)
        runs = result.scalars().all()

        items = [
            RunListItem(
                run_id=r.id,
                project_id=r.project_id,
                request_text=r.request_text[:100] + "..."
                if len(r.request_text or "") > 100
                else (r.request_text or ""),
                status=r.status,
                model_profile=r.model_profile or "unknown",
                started_at=r.started_at,
                completed_at=r.completed_at,
                total_latency_ms=r.total_latency_ms,
                total_tool_calls=r.tool_call_count,
                evidence_count=r.evidence_count,
            )
            for r in runs
        ]

        return PaginatedRuns(
            runs=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def get_project_stats(self, project_id: UUID) -> ProjectDashboardStats:
        stats_query = select(
            func.count(ResearchRun.id).label("total_runs"),
            func.sum(case((ResearchRun.status == RunStatus.COMPLETED, 1), else_=0)).label(
                "completed_runs"
            ),
            func.sum(case((ResearchRun.status == RunStatus.FAILED, 1), else_=0)).label(
                "failed_runs"
            ),
            func.sum(ResearchRun.total_latency_ms).label("total_latency_sum"),
            func.sum(ResearchRun.evidence_count).label("total_evidence"),
        ).where(ResearchRun.project_id == project_id)

        result = await self._session.execute(stats_query)
        stats = result.one_or_none()

        # NOTE: aggregate SUM() over an empty set returns NULL, not 0.
        total_runs = stats.total_runs if stats else 0
        completed_runs = (stats.completed_runs if stats else None) or 0
        failed_runs = (stats.failed_runs if stats else None) or 0
        total_latency = (stats.total_latency_sum if stats else None) or 0
        total_evidence = (stats.total_evidence if stats else None) or 0
        avg_latency = total_latency / total_runs if total_runs > 0 else 0.0

        project_result = await self._session.execute(
            select(Project.name).where(Project.id == project_id)
        )
        project_name = project_result.scalar_one_or_none()
        if project_name is None:
            raise ValueError(f"Project {project_id} not found")

        recent_query = (
            select(ResearchRun)
            .where(ResearchRun.project_id == project_id)
            .order_by(ResearchRun.started_at.desc())
            .limit(5)
        )
        recent_result = await self._session.execute(recent_query)
        recent_runs = [
            RunListItem(
                run_id=r.id,
                project_id=r.project_id,
                request_text=r.request_text[:100] + "..."
                if len(r.request_text or "") > 100
                else (r.request_text or ""),
                status=r.status,
                model_profile=r.model_profile or "unknown",
                started_at=r.started_at,
                completed_at=r.completed_at,
                total_latency_ms=r.total_latency_ms,
                total_tool_calls=r.tool_call_count,
                evidence_count=r.evidence_count,
            )
            for r in recent_result.scalars().all()
        ]

        return ProjectDashboardStats(
            project_id=project_id,
            project_name=project_name or f"Project {str(project_id)[:8]}",
            total_papers=await self._count_papers(project_id),
            total_runs=total_runs,
            completed_runs=completed_runs,
            failed_runs=failed_runs,
            total_evidence=total_evidence,
            avg_latency_ms=avg_latency,
            recent_runs=recent_runs,
        )

    async def _count_papers(self, project_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(Paper.id)).where(Paper.project_id == project_id)
        )
        return result.scalar() or 0

    async def get_comparison_dashboard(self, synthesis_id: UUID) -> ComparisonDashboardData:
        return ComparisonDashboardData(
            project_id=UUID(int=0),
            synthesis_id=synthesis_id,
            comparison_tables=[],
            gaps=[],
            conflicts=[],
            generated_at=datetime.utcnow(),
        )

    async def get_gaps_dashboard(self, project_id: UUID) -> list[GapDashboardItem]:
        return []

    async def get_conflicts_dashboard(self, project_id: UUID) -> list[ConflictDashboardItem]:
        return []

    async def get_evaluation_stats(self) -> EvaluationDashboardStats:
        return EvaluationDashboardStats(
            total_evaluations=0,
            total_tasks=0,
            avg_task_success=0.0,
            avg_citation_precision=0.0,
            avg_unsupported_claim_rate=0.0,
            avg_retrieval_precision_at_5=0.0,
            system_type_breakdown={},
            category_breakdown={},
            difficulty_breakdown={},
            recent_runs=[],
        )


async def get_trace_replay_service():
    async with get_session() as session:
        yield TraceReplayService(session)
