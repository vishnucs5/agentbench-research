from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ComparisonType(PyEnum):
    MODEL = "model"
    DATASET = "dataset"
    METRICS = "metrics"
    PREPROCESSING = "preprocessing"
    RESULTS = "results"
    LIMITATIONS = "limitations"


class ConflictType(PyEnum):
    INCOMPATIBLE_PREPROCESSING = "incompatible_preprocessing"
    DIFFERENT_METRIC_DEFINITIONS = "different_metric_definitions"
    CONFLICTING_RESULTS = "conflicting_results"
    INCONSISTENT_MODEL_CONFIG = "inconsistent_model_config"


class GapType(PyEnum):
    REPEATED_LIMITATION = "repeated_limitation"
    MISSING_EVALUATION = "missing_evaluation"
    UNEXPLORED_APPROACH = "unexplored_approach"
    DATA_GAP = "data_gap"


class NormalizedValue(BaseModel):
    value: Any
    unit: str | None = None
    confidence: float = 1.0
    source_claim_ids: list[UUID] = []


class ComparisonCell(BaseModel):
    paper_id: UUID
    paper_title: str
    value: NormalizedValue
    claim_id: UUID | None = None
    evidence_ids: list[str] = []


class ComparisonRow(BaseModel):
    attribute: str
    attribute_type: ComparisonType
    cells: list[ComparisonCell]
    has_conflicts: bool = False
    conflict_details: str | None = None


class ComparisonTable(BaseModel):
    table_id: UUID
    project_id: UUID
    paper_ids: list[UUID]
    comparison_type: ComparisonType
    rows: list[ComparisonRow]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conflict(BaseModel):
    conflict_id: UUID
    conflict_type: ConflictType
    paper_ids: list[UUID]
    description: str
    details: dict[str, Any] = {}
    severity: str = "medium"
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class Gap(BaseModel):
    gap_id: UUID
    gap_type: GapType
    paper_ids: list[UUID]
    description: str
    evidence_ids: list[str] = []
    frequency: int = 1
    severity: str = "medium"
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisRequest(BaseModel):
    project_id: UUID
    paper_ids: list[UUID]
    comparison_types: list[ComparisonType] = Field(default_factory=list)
    include_gaps: bool = True
    include_conflicts: bool = True


class SynthesisResponse(BaseModel):
    synthesis_id: UUID
    project_id: UUID
    comparison_tables: list[ComparisonTable]
    conflicts: list[Conflict]
    gaps: list[Gap]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizationRule(BaseModel):
    rule_id: UUID
    field: str
    pattern: str
    replacement: str
    description: str = ""


class NormalizedEntity(BaseModel):
    entity_type: str
    original_value: str
    normalized_value: str
    confidence: float
    aliases: list[str] = []
