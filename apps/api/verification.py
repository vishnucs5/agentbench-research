from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.extraction.service import get_extraction_service
from packages.retrieval.service import get_retrieval_service
from packages.synthesis.service import get_synthesis_service
from packages.verification.report_generator import get_report_generation_service
from packages.verification.schemas import (
    ReportRequest,
    ReportResponse,
    VerificationRequest,
    VerificationResult,
)
from packages.verification.verifier import get_citation_verification_service

router = APIRouter(prefix="/v1/projects/{project_id}/verification", tags=["verification"])


@router.post(
    "/verify",
    response_model=VerificationResult,
    status_code=status.HTTP_201_CREATED,
)
async def verify_draft(
    project_id: UUID,
    request: VerificationRequest,
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    verification_service=Depends(get_citation_verification_service),
):
    return await verification_service.verify_draft(request)


@router.post(
    "/report",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    project_id: UUID,
    request: ReportRequest,
    extraction_service=Depends(get_extraction_service),
    synthesis_service=Depends(get_synthesis_service),
    retrieval_service=Depends(get_retrieval_service),
    verification_service=Depends(get_citation_verification_service),
    report_service=Depends(get_report_generation_service),
):
    request.project_id = project_id
    return await report_service.generate_report(request)


@router.get("/job/{job_id}")
async def get_verification_job(
    project_id: UUID,
    job_id: UUID,
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Job status lookup not yet implemented",
    )
