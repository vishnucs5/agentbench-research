from __future__ import annotations

from typing import Any
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
from packages.evaluation.service import get_evaluation_service
from packages.extraction.service import get_extraction_service
from packages.retrieval.service import get_retrieval_service
from packages.security.middleware import get_current_user
from packages.synthesis.service import get_synthesis_service
from packages.verification.report_generator import get_report_generation_service
from packages.verification.verifier import get_citation_verification_service

router = APIRouter(prefix="/v1/evaluation", tags=["evaluation"])


def _get_synthesis_service(
    extraction_service: Any = Depends(get_extraction_service),
) -> Any:
    return get_synthesis_service(extraction_service)


def _get_verification_service(
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
) -> Any:
    return get_citation_verification_service(extraction_service, retrieval_service)


def _get_report_service(
    extraction_service: Any = Depends(get_extraction_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
) -> Any:
    return get_report_generation_service(
        extraction_service, synthesis_service, verification_service
    )


@router.post(
    "/run",
    response_model=EvaluationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    current_user: User = Depends(get_current_user),
    config: EvaluationConfig | None = None,
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
    report_service: Any = Depends(_get_report_service),
) -> EvaluationSummary:

    eval_service = get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )

    return await eval_service.run_evaluation(config)


@router.get("/runs", response_model=list[EvaluationRun])
async def list_evaluation_runs(
    current_user: User = Depends(get_current_user),
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
    report_service: Any = Depends(_get_report_service),
) -> list[EvaluationRun]:

    eval_service = get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )
    return eval_service.list_runs()


@router.get("/runs/{run_id}", response_model=EvaluationRun)
async def get_evaluation_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
    report_service: Any = Depends(_get_report_service),
) -> EvaluationRun:

    eval_service = get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
    report_service: Any = Depends(_get_report_service),
) -> dict[str, object]:

    eval_service = get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    results = eval_service.get_results(run_id)
    return {"run_id": str(run_id), "results": results}


@router.get("/runs/{run_id}/metrics")
async def get_run_metrics(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    extraction_service: Any = Depends(get_extraction_service),
    retrieval_service: Any = Depends(get_retrieval_service),
    synthesis_service: Any = Depends(_get_synthesis_service),
    verification_service: Any = Depends(_get_verification_service),
    report_service: Any = Depends(_get_report_service),
) -> dict[str, object]:

    eval_service = get_evaluation_service(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
    )
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
