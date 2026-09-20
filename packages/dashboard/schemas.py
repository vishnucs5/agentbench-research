from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class RunStatus(PyEnum):
    CREATED = "created"
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    EXTRACTING = "extracting"
    SYNTHESIZING = "synthesizing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"


class EventType(PyEnum):
    STATE_TRANSITION = "state_transition"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    CLAIM_EXTRACTED = "claim_extracted"
    CLAIM_VERIFIED = "claim_verified"
    ERROR = "error"
    BUDGET_WARNING = "budget_warning"
    LOOP_DETECTED = "loop_detected"


class TraceEventResponse(BaseModel):
    event_id: UUID
    sequence_no: int
    event_type: EventType
    component: str
    action: str | None = None
    status: str
    latency_ms: int | None = None
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    evidence_ids: list[str]
    model_profile: str | None = None
    redaction_version: str
    created_at: datetime


class RunTraceResponse(BaseModel):
    run_id: UUID
    project_id: UUID
    user_id: UUID
    request_text: str
    plan: list[dict[str, Any]]
    status: RunStatus
    model_profile: str
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    trace_events: list[TraceEventResponse]
    total_latency_ms: int
    total_tool_calls: int
    budgets: dict[str, Any]
    evidence_ids: list[str]


class RunListItem(BaseModel):
    run_id: UUID
    project_id: UUID
    request_text: str
    status: RunStatus
    model_profile: str
    started_at: datetime
    completed_at: datetime | None
    total_latency_ms: int
    total_tool_calls: int
    evidence_count: int


class ProjectDashboardStats(BaseModel):
    project_id: UUID
    project_name: str
    total_papers: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    total_evidence: int
    avg_latency_ms: float
    recent_runs: list[RunListItem]


class TraceFilter(BaseModel):
    event_types: list[EventType] | None = None
    components: list[str] | None = None
    statuses: list[str] | None = None
    start_sequence: int | None = None
    end_sequence: int | None = None
    include_evidence: bool = True
    include_redacted: bool = False


class DashboardFilters(BaseModel):
    project_ids: list[UUID] | None = None
    statuses: list[RunStatus] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    model_profiles: list[str] | None = None
    search_query: str | None = None
    page: int = 1
    page_size: int = 20


class PaginatedRuns(BaseModel):
    runs: list[RunListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComparisonDashboardData(BaseModel):
    project_id: UUID
    synthesis_id: UUID
    comparison_tables: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    generated_at: datetime


class GapDashboardItem(BaseModel):
    gap_id: UUID
    gap_type: str
    description: str
    frequency: int
    severity: str
    paper_ids: list[UUID]
    evidence_ids: list[str]
    detected_at: datetime


class ConflictDashboardItem(BaseModel):
    conflict_id: UUID
    conflict_type: str
    description: str
    severity: str
    paper_ids: list[UUID]
    details: dict[str, Any]
    detected_at: datetime


class EvaluationDashboardStats(BaseModel):
    total_evaluations: int
    total_tasks: int
    avg_task_success: float
    avg_citation_precision: float
    avg_unsupported_claim_rate: float
    avg_retrieval_precision_at_5: float
    system_type_breakdown: dict[str, int]
    category_breakdown: dict[str, int]
    difficulty_breakdown: dict[str, int]
    recent_runs: list[dict[str, Any]]
