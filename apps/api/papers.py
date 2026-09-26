from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from packages.domain.database import get_db_session
from packages.domain.models import Chunk, PaperPage, PaperStatus, Project, User
from packages.ingestion.schemas import (
    IngestionJobStatus,
    PaperIngestRequest,
    PaperIngestResponse,
    PaperListResponse,
    PaperStatusResponse,
)
from packages.ingestion.service import IngestionService, get_ingestion_service
from packages.security.middleware import get_current_user
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/projects/{project_id}/papers", tags=["papers"])


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> None:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


class PaperProcessResponse(BaseModel):
    paper_id: UUID
    status: str
    page_count: int
    chunk_count: int
    indexed: bool
    message: str


@router.post(
    "",
    response_model=PaperIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_paper(
    project_id: UUID,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    authors: str | None = Form(None),
    year: int | None = Form(None),
    doi: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: IngestionService = Depends(get_ingestion_service),
) -> PaperIngestResponse:
    await _require_owned_project(session, project_id, current_user)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    content = await file.read()
    await file.close()

    import json

    author_list = None
    if authors:
        try:
            author_list = json.loads(authors)
        except json.JSONDecodeError:
            author_list = [a.strip() for a in authors.split(",") if a.strip()]

    request = PaperIngestRequest(
        title=title,
        authors=author_list,
        year=year,
        doi=doi,
    )

    paper_id, result = await service.ingest_upload(
        project_id=project_id,
        file_data=content,
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
        request=request,
    )

    if result == "duplicate":
        return PaperIngestResponse(
            paper_id=paper_id,
            status="duplicate",
            message="Paper already exists (duplicate detected by SHA-256)",
        )

    # Automatically parse, chunk, and index the paper for immediate search and extraction
    try:
        parsed = await service.process_paper(paper_id)
        page_rows = (
            (await session.execute(select(PaperPage).where(PaperPage.paper_id == paper_id)))
            .scalars()
            .all()
        )
        if page_rows:
            page_ids = {p.page_number: p.id for p in page_rows}
            from packages.retrieval.chunker import ChunkingService

            chunker = ChunkingService()
            doc_chunks = chunker.chunk_paper(parsed, paper_id)
            for c in doc_chunks:
                pid = page_ids.get(c.page_number)
                if pid:
                    session.add(
                        Chunk(
                            paper_id=paper_id,
                            page_id=pid,
                            text=c.text,
                            token_count=c.token_count,
                            chunk_version="1.0.0",
                            metadata_json=dict(c.metadata or {}),
                        )
                    )
            await session.flush()
            from packages.retrieval.service import get_retrieval_service

            try:
                await get_retrieval_service().index_paper(
                    parsed,
                    str(paper_id),
                    str(project_id),
                    metadata={"paper_title": request.title or file.filename},
                )
            except Exception as idx_err:
                logger.warning("Vector indexing deferred: %s", idx_err)

            from packages.ingestion.repository import PaperRepository

            await PaperRepository(session).update_status(paper_id, PaperStatus.INDEXED)
    except Exception as e:
        logger.warning("Auto-processing paper deferred: %s", e)

    return PaperIngestResponse(
        paper_id=paper_id,
        status="created",
        message="Paper uploaded and processed successfully.",
    )


@router.get("", response_model=PaperListResponse)
async def list_papers(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PaperListResponse:
    await _require_owned_project(session, project_id, current_user)
    from packages.domain.models import PaperStatus
    from packages.ingestion.repository import PaperRepository

    repo = PaperRepository(session)

    paper_status = None
    if status_filter:
        try:
            paper_status = PaperStatus(status_filter)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            ) from e

    papers, total = await repo.get_by_project(
        project_id=project_id,
        page=page,
        page_size=page_size,
        status=paper_status,
    )

    return PaperListResponse(
        papers=[
            PaperStatusResponse(
                paper_id=p.id,
                title=p.title,
                status=p.status.value,
                parser_version=p.parser_version,
                page_count=len(p.pages) if p.pages else None,
                error=getattr(p, "error", None),
                created_at=p.created_at,
                updated_at=getattr(p, "updated_at", None),
            )
            for p in papers
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{paper_id}", response_model=PaperStatusResponse)
async def get_paper(
    project_id: UUID,
    paper_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PaperStatusResponse:
    await _require_owned_project(session, project_id, current_user)
    from packages.ingestion.repository import PaperRepository

    repo = PaperRepository(session)
    paper = await repo.get_by_id(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    return PaperStatusResponse(
        paper_id=paper.id,
        title=paper.title,
        status=paper.status.value,
        parser_version=paper.parser_version,
        page_count=len(paper.pages) if paper.pages else None,
        error=getattr(paper, "error", None),
        created_at=paper.created_at,
        updated_at=getattr(paper, "updated_at", None),
    )


@router.get("/{paper_id}/pages", response_model=None)
async def get_paper_pages(
    project_id: UUID,
    paper_id: UUID,
    page_number: int | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    await _require_owned_project(session, project_id, current_user)
    from packages.ingestion.repository import PaperRepository

    repo = PaperRepository(session)
    paper = await repo.get_by_id(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    if page_number is not None:
        page = next((p for p in paper.pages if p.page_number == page_number), None)
        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {page_number} not found",
            )
        return {
            "page_number": page.page_number,
            "text": page.text,
            "section_label": page.section_label,
            "char_count": len(page.text),
        }

    return {
        "pages": [
            {
                "page_number": p.page_number,
                "text": p.text,
                "section_label": p.section_label,
                "char_count": len(p.text),
            }
            for p in sorted(paper.pages, key=lambda x: x.page_number)
        ]
    }


@router.post("/{paper_id}/process", response_model=PaperProcessResponse)
async def process_paper_endpoint(
    project_id: UUID,
    paper_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: IngestionService = Depends(get_ingestion_service),
) -> PaperProcessResponse:
    """Parse a paper, persist chunks, and index for search (best-effort)."""
    await _require_owned_project(session, project_id, current_user)
    from packages.ingestion.repository import PaperRepository

    repo = PaperRepository(session)
    paper = await repo.get_by_id(paper_id)
    if not paper or paper.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    try:
        parsed = await service.process_paper(paper_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        await repo.update_status(paper_id, PaperStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        ) from e

    # Map page numbers to persisted page ids for chunk linkage
    page_rows = (
        (await session.execute(select(PaperPage).where(PaperPage.paper_id == paper_id)))
        .scalars()
        .all()
    )
    if not page_rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No pages persisted for paper",
        )
    page_ids = {p.page_number: p.id for p in page_rows}

    # Chunk and persist to DB (powers local BM25 fallback)
    from packages.retrieval.chunker import ChunkingService
    from sqlalchemy import delete

    # Delete existing chunks first to ensure idempotent re-processing
    await session.execute(delete(Chunk).where(Chunk.paper_id == paper_id))

    chunker = ChunkingService()
    doc_chunks = chunker.chunk_paper(parsed, paper_id)
    for c in doc_chunks:
        pid = page_ids.get(c.page_number)
        if pid is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing page {c.page_number} for paper {paper_id}",
            )
        session.add(
            Chunk(
                paper_id=paper_id,
                page_id=pid,
                text=c.text,
                token_count=c.token_count,
                chunk_version="1.0.0",
                metadata_json=dict(c.metadata or {}),
            )
        )
    await session.flush()

    # Best-effort vector/BM25 indexing (works without Qdrant/embeddings)
    indexed = False
    try:
        from packages.retrieval.service import get_retrieval_service

        stats = await get_retrieval_service().index_paper(
            parsed,
            str(paper_id),
            str(project_id),
            metadata={"paper_title": paper.title},
        )
        indexed = bool(stats.get("bm25_indexed"))
    except Exception:
        indexed = False

    await repo.update_status(paper_id, PaperStatus.INDEXED if indexed else PaperStatus.PARSED)

    return PaperProcessResponse(
        paper_id=paper_id,
        status=PaperStatus.INDEXED.value if indexed else PaperStatus.PARSED.value,
        page_count=len(parsed.pages),
        chunk_count=len(doc_chunks),
        indexed=indexed,
        message="Paper processed successfully"
        if indexed
        else "Paper parsed; search indexing deferred",
    )


@router.get("/{paper_id}/job/{job_id}", response_model=IngestionJobStatus)
async def get_ingestion_job(
    project_id: UUID,
    paper_id: UUID,
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionJobStatus:
    await _require_owned_project(session, project_id, current_user)
    job = service.get_job_status(job_id)
    if not job or job.paper_id != paper_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
