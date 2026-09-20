from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SearchType(PyEnum):
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    project_id: UUID | None = None
    paper_ids: list[UUID] | None = None
    author: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    topic: str | None = None
    search_type: SearchType = SearchType.HYBRID
    top_k: int = Field(default=10, ge=1, le=100)
    bm25_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class EvidenceHit(BaseModel):
    evidence_id: str
    paper_id: UUID
    paper_title: str
    page_number: int
    section_label: str | None = None
    text: str
    score: float
    search_type: SearchType
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    hits: list[EvidenceHit]
    total: int
    query: str
    search_type: SearchType
    took_ms: int
    not_enough_evidence: bool = False


class ChunkRequest(BaseModel):
    paper_id: UUID
    chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    preserve_sections: bool = True


class ChunkResponse(BaseModel):
    chunk_id: str
    paper_id: UUID
    page_number: int
    section_label: str | None
    text: str
    token_count: int
    embedding_created: bool


class IndexStatus(BaseModel):
    paper_id: UUID
    status: str
    chunk_count: int
    embedded_count: int
    bm25_indexed: bool
    error: str | None = None
    updated_at: datetime | None = None
