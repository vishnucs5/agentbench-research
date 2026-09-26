from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.domain.database import get_db_session
from packages.domain.models import Project, User
from packages.security.middleware import get_current_user
from packages.verification.report_generator import (
    ReportGenerationService,
    get_report_generation_service,
)
from packages.verification.schemas import (
    ReportRequest,
    ReportResponse,
    VerificationRequest,
    VerificationResult,
)
from packages.verification.verifier import (
    CitationVerificationService,
    get_citation_verification_service,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/projects/{project_id}/verification", tags=["verification"])


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> None:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/verify",
    response_model=VerificationResult,
    status_code=status.HTTP_201_CREATED,
)
async def verify_draft(
    project_id: UUID,
    request: VerificationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service),
) -> VerificationResult:
    await _require_owned_project(session, project_id, current_user)
    return await verification_service.verify_draft(request)


@router.post(
    "/report",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    project_id: UUID,
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportGenerationService = Depends(get_report_generation_service),
) -> ReportResponse:
    await _require_owned_project(session, project_id, current_user)
    request.project_id = project_id
    return await report_service.generate_report(request)


@router.get("/job/{job_id}")
async def get_verification_job(
    project_id: UUID,
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await _require_owned_project(session, project_id, current_user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Job status lookup not yet implemented",
    )
