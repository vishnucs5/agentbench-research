from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VerificationStatus(PyEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    OPINION = "opinion"
    NOT_REPORTED = "not_reported"


class AtomicClaimStatus(PyEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNSUPPORTED = "unsupported"
    OPINION = "opinion"
    NOT_REPORTED = "not_reported"
    CONTRADICTED = "contradicted"


class VerificationRequest(BaseModel):
    draft_text: str = Field(..., min_length=1)
    evidence_ids: list[str] | None = None
    paper_ids: list[UUID] | None = None
    strict_mode: bool = False


class AtomicClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str  # factual, opinion, interpretation
    status: AtomicClaimStatus = AtomicClaimStatus.NOT_REPORTED
    supporting_evidence: list[str] = []
    contradicting_evidence: list[str] = []
    confidence: float = 0.0
    rationale: str | None = None


class VerificationResult(BaseModel):
    overall_status: VerificationStatus
    atomic_claims: list[AtomicClaim]
    unsupported_claims: list[str]
    citation_coverage: float = 0.0
    total_claims: int = 0
    verified_claims: int = 0
    partially_verified_claims: int = 0
    unsupported_claims_count: int = 0
    opinion_claims: int = 0
    details: dict[str, Any] = {}


class ReportSection(BaseModel):
    section_id: str
    title: str
    content: str
    citations: list[str] = []
    evidence_ids: list[str] = []


class ReportRequest(BaseModel):
    project_id: UUID
    paper_ids: list[UUID]
    synthesis_id: UUID | None = None
    include_comparison_tables: bool = True
    include_gaps: bool = True
    include_conflicts: bool = True
    include_uncertainty: bool = True
    custom_sections: list[str] | None = None
    template: str | None = "standard"


class ReportResponse(BaseModel):
    report_id: UUID
    project_id: UUID
    title: str
    sections: list[ReportSection]
    executive_summary: str
    uncertainty_section: str | None = None
    citations: list[str] = []
    evidence_ids: list[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    verification_result: VerificationResult | None = None


class Citation(BaseModel):
    citation_id: str
    paper_id: UUID
    paper_title: str
    authors: list[str] = []
    year: int | None = None
    doi: str | None = None
    evidence_ids: list[str] = []
    claim_text: str
    quote: str | None = None
    page_numbers: list[int] = []


class BibliographyEntry(BaseModel):
    entry_id: str
    paper_id: UUID
    formatted_citation: str
    paper_title: str
    authors: list[str]
    year: int | None = None
    doi: str | None = None
    source_url: str | None = None


class VerificationJobStatus(BaseModel):
    job_id: UUID
    project_id: UUID
    status: str
    progress: float
    current_step: str
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
