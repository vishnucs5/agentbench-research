from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.extraction.service import ExtractionService, get_extraction_service
from packages.synthesis.schemas import (
    SynthesisRequest,
    SynthesisResponse,
)
from packages.synthesis.service import SynthesisService, get_synthesis_service

router = APIRouter(prefix="/v1/projects/{project_id}/synthesis", tags=["synthesis"])


@router.post(
    "",
    response_model=SynthesisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_synthesis(
    project_id: UUID,
    request: SynthesisRequest,
    extraction_service: ExtractionService = Depends(get_extraction_service),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
) -> SynthesisResponse:
    request.project_id = project_id
    return await synthesis_service.run_synthesis(request)


@router.get("/comparisons", response_model=None)
async def list_comparisons(
    project_id: UUID,
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past comparisons not yet implemented",
    )


@router.get("/conflicts", response_model=None)
async def list_conflicts(
    project_id: UUID,
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past conflicts not yet implemented",
    )


@router.get("/gaps", response_model=None)
async def list_gaps(
    project_id: UUID,
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing past gaps not yet implemented",
    )
