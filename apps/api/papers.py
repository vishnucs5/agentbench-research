from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from packages.domain.database import get_db_session
from packages.ingestion.schemas import (
    IngestionJobStatus,
    PaperIngestRequest,
    PaperIngestResponse,
    PaperListResponse,
    PaperStatusResponse,
)
from packages.ingestion.service import IngestionService, get_ingestion_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/projects/{project_id}/papers", tags=["papers"])


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
    service: IngestionService = Depends(get_ingestion_service),
):
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

    return PaperIngestResponse(
        paper_id=paper_id,
        status="created",
        message="Paper uploaded successfully. Processing started.",
    )


@router.get("", response_model=PaperListResponse)
async def list_papers(
    project_id: UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
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
    session: AsyncSession = Depends(get_db_session),
):
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
    session: AsyncSession = Depends(get_db_session),
):
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


@router.get("/{paper_id}/job/{job_id}", response_model=IngestionJobStatus)
async def get_ingestion_job(
    project_id: UUID,
    paper_id: UUID,
    job_id: UUID,
    service: IngestionService = Depends(get_ingestion_service),
):
    job = service.get_job_status(job_id)
    if not job or job.paper_id != paper_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
