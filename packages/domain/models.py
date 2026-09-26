from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .models import (
        BenchmarkTask,
        Chunk,
        Claim,
        Evaluation,
        EvidenceLink,
        Paper,
        PaperPage,
        PlagiarismCheck,
        PlagiarismMatch,
        Project,
        ResearchRun,
        TraceEvent,
        User,
    )


class Base(DeclarativeBase):
    pass


class UserRole(str, PyEnum):
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class PaperStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    INDEXED = "indexed"
    FAILED = "failed"


class RunStatus(str, PyEnum):
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


class ClaimStatus(str, PyEnum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNSUPPORTED = "unsupported"
    OPINION = "opinion"
    NOT_REPORTED = "not_reported"


class SupportType(str, PyEnum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTRADICTS = "contradicts"
    UNRELATED = "unrelated"


class EventType(str, PyEnum):
    STATE_TRANSITION = "state_transition"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    CLAIM_EXTRACTED = "claim_extracted"
    CLAIM_VERIFIED = "claim_verified"
    ERROR = "error"
    BUDGET_WARNING = "budget_warning"
    LOOP_DETECTED = "loop_detected"


class PlagiarismCheckStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlagiarismSourceType(str, PyEnum):
    INTERNAL = "internal"
    EXTERNAL_API = "external_api"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=UserRole.RESEARCHER,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    projects: Mapped[list[Project]] = relationship(back_populates="owner", lazy="selectin")
    runs: Mapped[list[ResearchRun]] = relationship(back_populates="user", lazy="selectin")
    plagiarism_checks: Mapped[list[PlagiarismCheck]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = ()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(
        String(100), default="network-intrusion-detection", nullable=False
    )
    retention_days: Mapped[int] = mapped_column(default=90, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="projects", lazy="selectin")
    papers: Mapped[list[Paper]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    runs: Mapped[list[ResearchRun]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    plagiarism_checks: Mapped[list[PlagiarismCheck]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_projects_owner_id", "owner_id"),)


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    year: Mapped[int | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PaperStatus] = mapped_column(
        Enum(
            PaperStatus,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=PaperStatus.UPLOADED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="papers", lazy="selectin")
    pages: Mapped[list[PaperPage]] = relationship(
        back_populates="paper", lazy="selectin", cascade="all, delete-orphan"
    )
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="paper", lazy="selectin", cascade="all, delete-orphan"
    )
    claims: Mapped[list[Claim]] = relationship(
        back_populates="paper", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_papers_project_id", "project_id"),)


class PaperPage(Base):
    __tablename__ = "paper_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    section_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocr_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="pages", lazy="selectin")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="page", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("paper_id", "page_number", name="uq_paper_page_number"),
        Index("ix_paper_pages_paper_id", "paper_id"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_pages.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(nullable=False)
    embedding_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_version: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="chunks", lazy="selectin")
    page: Mapped[PaperPage] = relationship(back_populates="chunks", lazy="selectin")
    evidence_links: Mapped[list[EvidenceLink]] = relationship(
        back_populates="chunk", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_chunks_paper_id", "paper_id"),)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    claim_type: Mapped[str] = mapped_column(String(100), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(
            ClaimStatus,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=ClaimStatus.EXTRACTED,
        nullable=False,
    )
    created_by_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    paper: Mapped[Paper] = relationship(back_populates="claims", lazy="selectin")
    evidence_links: Mapped[list[EvidenceLink]] = relationship(
        back_populates="claim", lazy="selectin", cascade="all, delete-orphan"
    )
    run: Mapped[ResearchRun | None] = relationship(lazy="selectin")

    __table_args__ = (Index("ix_claims_paper_id", "paper_id"),)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(nullable=False)
    support_type: Mapped[SupportType] = mapped_column(
        Enum(
            SupportType,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=SupportType.SUPPORTS,
        nullable=False,
    )
    match_score: Mapped[float] = mapped_column(default=0.0, nullable=False)

    claim: Mapped[Claim] = relationship(back_populates="evidence_links", lazy="selectin")
    chunk: Mapped[Chunk] = relationship(back_populates="evidence_links", lazy="selectin")

    __table_args__ = (Index("ix_evidence_links_claim_id", "claim_id"),)


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(
            RunStatus,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=RunStatus.CREATED,
        nullable=False,
    )
    model_profile: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Denormalized metrics (computed on run completion)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    trace_event_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    project: Mapped[Project] = relationship(back_populates="runs", lazy="selectin")
    user: Mapped[User] = relationship(back_populates="runs", lazy="selectin")
    trace_events: Mapped[list[TraceEvent]] = relationship(
        back_populates="run",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="TraceEvent.sequence_no",
    )
    evaluations: Mapped[list[Evaluation]] = relationship(
        back_populates="run", lazy="selectin", cascade="all, delete-orphan"
    )
    claims: Mapped[list[Claim]] = relationship(back_populates="run", lazy="selectin")

    __table_args__ = (Index("ix_research_runs_project_id", "project_id"),)


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
    )
    component: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    model_profile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    redaction_version: Mapped[str] = mapped_column(String(50), default="redact-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[ResearchRun] = relationship(back_populates="trace_events", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("run_id", "sequence_no", name="uq_trace_sequence"),
        Index("ix_trace_events_run_id", "run_id"),
    )


class BenchmarkTask(Base):
    __tablename__ = "benchmark_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_version: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    gold_answer_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    gold_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    difficulty: Mapped[Literal["easy", "medium", "hard"]] = mapped_column(
        String(20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="task", lazy="selectin")

    __table_args__ = (Index("ix_benchmark_tasks_version", "benchmark_version"),)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmark_tasks.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    scorer_version: Mapped[str] = mapped_column(String(50), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[ResearchRun] = relationship(back_populates="evaluations", lazy="selectin")
    task: Mapped[BenchmarkTask] = relationship(back_populates="evaluations", lazy="selectin")

    __table_args__ = (Index("ix_evaluations_run_id", "run_id"),)


class PlagiarismCheck(Base):
    __tablename__ = "plagiarism_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[PlagiarismCheckStatus] = mapped_column(
        Enum(
            PlagiarismCheckStatus,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        default=PlagiarismCheckStatus.PENDING,
        nullable=False,
    )
    overall_similarity: Mapped[float] = mapped_column(default=0.0, nullable=False)
    originality_score: Mapped[float] = mapped_column(default=100.0, nullable=False)
    total_matches: Mapped[int] = mapped_column(default=0, nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), default="internal", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    consented_to_store: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(lazy="selectin")
    project: Mapped[Project | None] = relationship(lazy="selectin")
    matches: Mapped[list[PlagiarismMatch]] = relationship(
        back_populates="check", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_plagiarism_checks_user_id", "user_id"),
        Index("ix_plagiarism_checks_project_id", "project_id"),
        Index("ix_plagiarism_checks_status", "status"),
        Index("ix_plagiarism_checks_created_at", "created_at"),
    )


class PlagiarismMatch(Base):
    __tablename__ = "plagiarism_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plagiarism_checks.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[PlagiarismSourceType] = mapped_column(
        Enum(
            PlagiarismSourceType,
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
    )
    matched_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_document_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_start_offset: Mapped[int | None] = mapped_column(nullable=True)
    match_end_offset: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )

    check: Mapped[PlagiarismCheck] = relationship(back_populates="matches", lazy="selectin")

    __table_args__ = (
        Index("ix_plagiarism_matches_check_id", "check_id"),
        Index("ix_plagiarism_matches_source_type", "source_type"),
        Index("ix_plagiarism_matches_source_document_id", "source_document_id"),
    )
