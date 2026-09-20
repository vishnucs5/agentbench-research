from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class PaperSourceType(PyEnum):
    UPLOAD = "upload"
    URL = "url"


class PaperIngestRequest(BaseModel):
    source_type: PaperSourceType = PaperSourceType.UPLOAD
    source_url: HttpUrl | None = None
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None


class PaperIngestResponse(BaseModel):
    paper_id: UUID
    status: str
    message: str


class PaperStatusResponse(BaseModel):
    paper_id: UUID
    title: str
    status: str
    parser_version: str
    page_count: int | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class PaperPageResponse(BaseModel):
    page_number: int
    text: str
    section_label: str | None = None
    char_count: int
    token_count: int


class PaperListResponse(BaseModel):
    papers: list[PaperStatusResponse]
    total: int
    page: int
    page_size: int


class IngestionJobStatus(BaseModel):
    job_id: UUID
    paper_id: UUID
    status: str
    progress: float
    current_step: str
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class PaperMetadata(BaseModel):
    title: str | None = None
    authors: list[dict[str, Any]] = []
    year: int | None = None
    subject: str | None = None
    keywords: list[str] = []
    producer: str | None = None
    creator: str | None = None
    creation_date: datetime | None = None
    modification_date: datetime | None = None
    page_count: int = 0


class ParsedPage(BaseModel):
    page_number: int
    text: str
    section_label: str | None = None
    char_count: int
    token_count: int
    ocr_used: bool = False


class ParsedPaper(BaseModel):
    metadata: PaperMetadata
    pages: list[ParsedPage]
    parser_version: str
    sha256: str
