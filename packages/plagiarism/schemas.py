from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PlagiarismCheckStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlagiarismSourceType(str, PyEnum):
    INTERNAL = "internal"
    EXTERNAL_API = "external_api"


class PlagiarismCheckRequest(BaseModel):
    """Request to check text for plagiarism."""

    text: str | None = Field(
        default=None,
        description="Text content to check (alternative to file upload)",
        min_length=1,
        max_length=1000000,
    )
    project_id: UUID | None = Field(
        default=None,
        description="Optional project ID to limit comparison scope",
    )
    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold (0.0-1.0)",
    )
    consented_to_store: bool = Field(
        default=False,
        description="Whether to store the submitted text and matches permanently",
    )


class PlagiarismFileCheckRequest(BaseModel):
    """Request to check uploaded file for plagiarism."""

    project_id: UUID | None = None
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    consented_to_store: bool = False


class PlagiarismMatchResponse(BaseModel):
    """Individual match in plagiarism report."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: PlagiarismSourceType
    matched_text: str
    source_text: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_document_id: UUID | None = None
    source_document_title: str | None = None
    source_url: HttpUrl | None = None
    source_location: str | None = None
    match_start_offset: int | None = None
    match_end_offset: int | None = None
    created_at: datetime


class PlagiarismCheckResponse(BaseModel):
    """Response for a plagiarism check."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    project_id: UUID | None = None
    source_filename: str | None = None
    source_mime_type: str | None = None
    source_size_bytes: int | None = None
    status: PlagiarismCheckStatus
    overall_similarity: float = Field(ge=0.0, le=1.0)
    originality_score: float = Field(ge=0.0, le=100.0)
    total_matches: int
    provider_used: str
    error_message: str | None = None
    consented_to_store: bool
    created_at: datetime
    completed_at: datetime | None = None


class PlagiarismReportResponse(BaseModel):
    """Complete plagiarism report with matches."""

    check: PlagiarismCheckResponse
    matches: list[PlagiarismMatchResponse]
    summary: str


class PlagiarismListResponse(BaseModel):
    """Paginated list of plagiarism checks."""

    checks: list[PlagiarismCheckResponse]
    total: int
    page: int
    page_size: int


class PlagiarismErrorResponse(BaseModel):
    """Error response for plagiarism endpoints."""

    detail: str
    error_code: str | None = None


class SupportedFileTypesResponse(BaseModel):
    """Response with supported file types."""

    mime_types: list[str]
    extensions: list[str]
    max_size_mb: int
