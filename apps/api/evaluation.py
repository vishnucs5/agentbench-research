from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/v1/evaluation", tags=["evaluation"])


@router.post(
    "/run",
    response_model=EvaluationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    config: EvaluationConfig | None = None,
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    synthesis_service=Depends(lambda: None),
    verification_service=Depends(lambda: None),
    report_service=Depends(lambda: None),
):

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
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    synthesis_service=Depends(lambda: None),
    verification_service=Depends(lambda: None),
    report_service=Depends(lambda: None),
):

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
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    synthesis_service=Depends(lambda: None),
    verification_service=Depends(lambda: None),
    report_service=Depends(lambda: None),
):

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
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    synthesis_service=Depends(lambda: None),
    verification_service=Depends(lambda: None),
    report_service=Depends(lambda: None),
):

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
    extraction_service=Depends(get_extraction_service),
    retrieval_service=Depends(get_retrieval_service),
    synthesis_service=Depends(lambda: None),
    verification_service=Depends(lambda: None),
    report_service=Depends(lambda: None),
):

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
async def list_categories():
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in TaskCategory]


@router.get("/benchmark/difficulties")
async def list_difficulties():
    return [{"value": d.value, "label": d.value.title()} for d in Difficulty]
