from __future__ import annotations

import inspect
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.domain.database import get_db_session
from packages.domain.models import PaperStatus, Project, User
from packages.extraction.schemas import (
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    ClaimStatus,
    ClaimType,
    EvidenceLinkRequest,
    EvidenceLinkResponse,
    ExtractionJobStatus,
)
from packages.extraction.service import ExtractionService, get_extraction_service
from packages.security.middleware import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/projects/{project_id}/papers/{paper_id}/extraction", tags=["extraction"])


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> None:
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.owner_id == current_user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )


@router.post(
    "",
    response_model=list[ClaimExtractionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def extract_claims(
    project_id: UUID,
    paper_id: UUID,
    request: ClaimExtractionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ExtractionService = Depends(get_extraction_service),
) -> list[ClaimExtractionResponse]:
    await _require_owned_project(session, project_id, current_user)
    from packages.ingestion.repository import PaperRepository

    repo = PaperRepository(session)
    paper = await repo.get_by_id(paper_id)

    if not paper or paper.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    if paper.status not in (PaperStatus.PARSED, PaperStatus.INDEXED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper must be parsed before extraction",
        )

    from packages.ingestion.parser import create_parser
    parser = create_parser()
    pdf_data = await get_paper_pdf(paper_id, session)
    parsed = parser.parse(pdf_data)

    return await service.extract_claims(paper_id, parsed, request)


async def get_paper_pdf(
    paper_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> bytes:
    from packages.ingestion.repository import PaperRepository
    from packages.ingestion.storage import get_storage_service

    repo = PaperRepository(session)
    paper = await repo.get_by_id(paper_id)

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    storage = get_storage_service()
    result: Any = storage.download_file(paper.storage_key)
    if inspect.isawaitable(result):
        return cast(bytes, await result)
    return cast(bytes, result)


@router.get("", response_model=list[ClaimExtractionResponse])
async def list_claims(
    project_id: UUID,
    paper_id: UUID,
    claim_type: ClaimType | None = None,
    claim_status: ClaimStatus | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ExtractionService = Depends(get_extraction_service),
) -> list[ClaimExtractionResponse]:
    await _require_owned_project(session, project_id, current_user)
    claims = await service.get_paper_claims(paper_id)

    if claim_type:
        claims = [c for c in claims if c.claim_type == claim_type]
    if claim_status:
        claims = [c for c in claims if c.status == claim_status]

    return claims


@router.get("/{claim_id}", response_model=ClaimExtractionResponse)
async def get_claim(
    project_id: UUID,
    paper_id: UUID,
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ExtractionService = Depends(get_extraction_service),
) -> ClaimExtractionResponse:
    await _require_owned_project(session, project_id, current_user)
    claim = await service.get_claim(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    return claim


@router.post("/evidence", response_model=EvidenceLinkResponse, status_code=status.HTTP_201_CREATED)
async def add_evidence_link(
    project_id: UUID,
    paper_id: UUID,
    request: EvidenceLinkRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ExtractionService = Depends(get_extraction_service),
) -> EvidenceLinkResponse:
    await _require_owned_project(session, project_id, current_user)
    return await service.link_evidence(request)


@router.get("/job/{job_id}", response_model=ExtractionJobStatus)
async def get_extraction_job(
    project_id: UUID,
    paper_id: UUID,
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ExtractionService = Depends(get_extraction_service),
) -> ExtractionJobStatus:
    await _require_owned_project(session, project_id, current_user)
    job = service.get_job_status(job_id)
    if not job or job.paper_id != paper_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
