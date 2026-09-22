from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.domain.database import get_db_session
from packages.domain.models import Project, User
from packages.extraction.service import ExtractionService, get_extraction_service
from packages.security.middleware import get_current_user
from packages.synthesis.schemas import (
    SynthesisRequest,
    SynthesisResponse,
)
from packages.synthesis.service import SynthesisService, get_synthesis_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/projects/{project_id}/synthesis", tags=["synthesis"])


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
    response_model=SynthesisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_synthesis(
    project_id: UUID,
    request: SynthesisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
) -> SynthesisResponse:
    await _require_owned_project(session, project_id, current_user)
    request.project_id = project_id
    return await synthesis_service.run_synthesis(request)


@router.get("/comparisons", response_model=None)
async def list_comparisons(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
) -> None:
    await _require_owned_project(session, project_id, current_user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past comparisons not yet implemented",
    )


@router.get("/conflicts", response_model=None)
async def list_conflicts(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
) -> None:
    await _require_owned_project(session, project_id, current_user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past conflicts not yet implemented",
    )


@router.get("/gaps", response_model=None)
async def list_gaps(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
) -> None:
    await _require_owned_project(session, project_id, current_user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past gaps not yet implemented",
    )
