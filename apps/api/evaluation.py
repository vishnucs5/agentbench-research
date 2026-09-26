from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.domain.models import User
from packages.evaluation.schemas import (
    Difficulty,
    EvaluationConfig,
    EvaluationRun,
    EvaluationSummary,
    TaskCategory,
)
from packages.evaluation.service import EvaluationService, get_evaluation_service
from packages.extraction.service import ExtractionService, get_extraction_service
from packages.retrieval.service import RetrievalService, get_retrieval_service
from packages.security.middleware import get_current_user
from packages.synthesis.service import SynthesisService, get_synthesis_service
from packages.verification.report_generator import (
    ReportGenerationService,
    get_report_generation_service,
)
from packages.verification.verifier import (
    CitationVerificationService,
    get_citation_verification_service,
)

router = APIRouter(prefix="/v1/evaluation", tags=["evaluation"])


def get_eval_service(
    extraction_service: ExtractionService = Depends(get_extraction_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    synthesis_service: SynthesisService = Depends(get_synthesis_service),
    verification_service: CitationVerificationService = Depends(get_citation_verification_service),
    report_service: ReportGenerationService = Depends(get_report_generation_service),
) -> EvaluationService:
    return get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )


@router.post(
    "/run",
    response_model=EvaluationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    current_user: User = Depends(get_current_user),
    config: EvaluationConfig | None = None,
    eval_service: EvaluationService = Depends(get_eval_service),
) -> EvaluationSummary:
    return await eval_service.run_evaluation(config)


@router.get("/runs", response_model=list[EvaluationRun])
async def list_evaluation_runs(
    current_user: User = Depends(get_current_user),
    eval_service: EvaluationService = Depends(get_eval_service),
) -> list[EvaluationRun]:
    return eval_service.list_runs()


@router.get("/runs/{run_id}", response_model=EvaluationRun)
async def get_evaluation_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    eval_service: EvaluationService = Depends(get_eval_service),
) -> EvaluationRun:
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    eval_service: EvaluationService = Depends(get_eval_service),
) -> dict[str, object]:
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    results = eval_service.get_results(run_id)
    return {"run_id": str(run_id), "results": results}


@router.get("/runs/{run_id}/metrics")
async def get_run_metrics(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    eval_service: EvaluationService = Depends(get_eval_service),
) -> dict[str, object]:
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    metrics = eval_service.get_metrics(run_id)
    return {"run_id": str(run_id), "metrics": metrics}


@router.get("/benchmark/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in TaskCategory]


@router.get("/benchmark/difficulties")
async def list_difficulties(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    return [{"value": d.value, "label": d.value.title()} for d in Difficulty]
