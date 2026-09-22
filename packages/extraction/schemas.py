from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ClaimType(PyEnum):
    RESEARCH_PROBLEM = "research_problem"
    DATASET = "dataset"
    PREPROCESSING = "preprocessing"
    MODEL = "model"
    METRICS = "metrics"
    RESULTS = "results"
    LIMITATIONS = "limitations"
    FUTURE_WORK = "future_work"


class ClaimStatus(PyEnum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNSUPPORTED = "unsupported"
    OPINION = "opinion"
    NOT_REPORTED = "not_reported"


class SupportType(PyEnum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTRADICTS = "contradicts"
    UNRELATED = "unrelated"


class ResearchProblemClaim(BaseModel):
    problem_statement: str | None = None
    motivation: str | None = None
    hypotheses: list[str] = []
    research_questions: list[str] = []
    objectives: list[str] = []


class DatasetClaim(BaseModel):
    name: str | None = None
    description: str | None = None
    size: str | None = None
    splits: dict[str, Any] = {}
    source: str | None = None
    language: str | None = None
    domain: str | None = None
    collection_method: str | None = None
    statistics: dict[str, Any] = {}


class PreprocessingClaim(BaseModel):
    steps: list[str] = []
    tools: list[str] = []
    parameters: dict[str, Any] = {}
    tokenization: str | None = None
    normalization: str | None = None
    filtering_criteria: str | None = None


class ModelClaim(BaseModel):
    name: str | None = None
    architecture: str | None = None
    framework: str | None = None
    parameters: str | None = None
    training_details: dict[str, Any] = {}
    hyperparameters: dict[str, Any] = {}
    pretrained: bool | None = None
    baseline_models: list[str] = []


class MetricsClaim(BaseModel):
    metrics: list[str] = []
    metric_definitions: dict[str, str] = {}
    evaluation_protocol: str | None = None
    significance_testing: str | None = None


class ResultsClaim(BaseModel):
    metric_results: dict[str, dict[str, Any]] = {}
    best_results: dict[str, Any] = {}
    statistical_significance: dict[str, Any] = {}
    comparison_results: dict[str, Any] = {}
    qualitative_findings: list[str] = []


class LimitationClaim(BaseModel):
    limitation_text: str | None = None
    severity: str | None = None
    category: str | None = None
    impact: str | None = None
    mitigation: str | None = None


class FutureWorkClaim(BaseModel):
    suggestion: str | None = None
    priority: str | None = None
    category: str | None = None
    rationale: str | None = None


CLAIM_SCHEMAS = {
    ClaimType.RESEARCH_PROBLEM: ResearchProblemClaim,
    ClaimType.DATASET: DatasetClaim,
    ClaimType.PREPROCESSING: PreprocessingClaim,
    ClaimType.MODEL: ModelClaim,
    ClaimType.METRICS: MetricsClaim,
    ClaimType.RESULTS: ResultsClaim,
    ClaimType.LIMITATIONS: LimitationClaim,
    ClaimType.FUTURE_WORK: FutureWorkClaim,
}


class ClaimExtractionRequest(BaseModel):
    paper_id: UUID
    claim_types: list[ClaimType] = Field(default_factory=list)
    chunk_ids: list[str] | None = None
    force_reextract: bool = False


class ClaimExtractionResponse(BaseModel):
    claim_id: UUID
    claim_type: ClaimType
    claim_text: str
    normalized_value: dict[str, Any]
    confidence: float
    status: ClaimStatus
    evidence_ids: list[str] = []
    paper_title: str | None = None


class EvidenceLinkRequest(BaseModel):
    claim_id: UUID
    chunk_id: UUID | str
    page_number: int
    support_type: SupportType = SupportType.SUPPORTS
    match_score: float = 0.0


class EvidenceLinkResponse(BaseModel):
    evidence_id: str
    claim_id: UUID
    chunk_id: UUID
    page_number: int
    support_type: SupportType
    match_score: float


class ExtractionJobStatus(BaseModel):
    job_id: UUID
    paper_id: UUID
    status: str
    progress: float
    current_claim_type: str | None = None
    claims_extracted: int = 0
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
