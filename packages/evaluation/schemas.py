from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskCategory(PyEnum):
    METADATA_EXTRACTION = "metadata_extraction"
    METHOD_EXTRACTION = "method_extraction"
    RESULT_EXTRACTION = "result_extraction"
    COMPARISON = "comparison"
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    GAP_ANALYSIS = "gap_analysis"
    CITATION_VERIFICATION = "citation_verification"
    FAILURE_RECOVERY = "failure_recovery"


class Difficulty(PyEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MetricType(PyEnum):
    TASK_SUCCESS = "task_success"
    CITATION_PRECISION = "citation_precision"
    UNSUPPORTED_CLAIM_RATE = "unsupported_claim_rate"
    RETRIEVAL_PRECISION_AT_5 = "retrieval_precision_at_5"
    TOOL_EFFICIENCY = "tool_efficiency"
    TRACE_COMPLETENESS = "trace_completeness"
    EXACT_MATCH = "exact_match"
    F1_SCORE = "f1_score"
    SEMANTIC_SIMILARITY = "semantic_similarity"


class BenchmarkTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    benchmark_version: str = "1.0.0"
    category: TaskCategory
    prompt: str
    paper_ids: list[UUID] = Field(default_factory=list)
    gold_answer: dict[str, Any]
    gold_evidence_ids: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.MEDIUM
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    benchmark_version: str
    model_profile: str
    system_type: str  # "direct_llm", "static_rag", "adaptive_agent"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str = "running"
    total_tasks: int = 0
    completed_tasks: int = 0
    results: list[Any] = Field(default_factory=list)


class TaskResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    evaluation_run_id: UUID
    task_id: UUID
    system_output: dict[str, Any]
    system_evidence_ids: list[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    trace_events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class MetricResult(BaseModel):
    metric_id: UUID = Field(default_factory=uuid4)
    evaluation_run_id: UUID
    task_id: UUID | None = None
    metric_name: MetricType
    value: float
    details: dict[str, Any] = Field(default_factory=dict)
    scorer_version: str = "1.0.0"
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationSummary(BaseModel):
    evaluation_run_id: UUID
    system_type: str
    model_profile: str
    benchmark_version: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    task_success_rate: float
    citation_precision: float
    unsupported_claim_rate: float
    retrieval_precision_at_5: float
    tool_efficiency: float
    trace_completeness: float
    avg_execution_time_ms: float
    category_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    difficulty_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)


class EvaluationConfig(BaseModel):
    benchmark_version: str = "1.0.0"
    model_profile: str = "balanced"
    system_type: str = "adaptive_agent"  # "direct_llm", "static_rag", "adaptive_agent"
    categories: list[TaskCategory] | None = None
    difficulties: list[Difficulty] | None = None
    max_concurrent: int = 1
    timeout_per_task_seconds: int = 300
    random_seed: int = 42
