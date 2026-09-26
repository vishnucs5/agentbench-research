from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from packages.evaluation.runner import (
    EvaluationRunner,
    MetricCalculator,
    compute_evaluation_summary,
)
from packages.evaluation.schemas import (
    BenchmarkTask,
    Difficulty,
    EvaluationConfig,
    EvaluationRun,
    MetricType,
    TaskCategory,
    TaskResult,
)
from packages.evaluation.service import EvaluationService


def test_metric_calculator():
    # Exact match
    assert MetricCalculator.calculate_exact_match("abc", "abc") == 1.0
    assert MetricCalculator.calculate_exact_match("abc", "def") == 0.0

    # F1 score
    gold = {"metric": "accuracy", "val": 0.98}
    pred = {"metric": "accuracy", "val": 0.98}
    assert MetricCalculator.calculate_f1_score(gold, pred) == 1.0

    pred_partial = {"metric": "accuracy"}
    assert 0.0 < MetricCalculator.calculate_f1_score(gold, pred_partial) < 1.0

    # Retrieval precision at 5
    gold_ev = ["ev-1", "ev-2"]
    pred_ev = ["ev-1", "ev-3", "ev-4"]
    p5 = MetricCalculator.calculate_retrieval_precision_at_5(gold_ev, pred_ev)
    assert p5 == 0.5

    # Verification precision & unsupported rate
    verification_payload = {
        "atomic_claims": [
            {"status": "verified"},
            {"status": "unsupported"},
        ]
    }
    assert MetricCalculator.calculate_citation_precision(verification_payload) == 0.5
    assert MetricCalculator.calculate_unsupported_claim_rate(verification_payload) == 0.5


def test_compute_evaluation_summary():
    task_id = uuid.uuid4()
    task = BenchmarkTask(
        task_id=task_id,
        category=TaskCategory.RESULT_EXTRACTION,
        prompt="What is the accuracy?",
        gold_answer={"accuracy": 0.98},
        gold_evidence_ids=["ev-1"],
        difficulty=Difficulty.EASY,
    )

    run = EvaluationRun(
        benchmark_version="1.0.0",
        model_profile="fast",
        system_type="direct_llm",
        total_tasks=1,
        completed_tasks=1,
    )

    result = TaskResult(
        evaluation_run_id=run.run_id,
        task_id=task_id,
        system_output={"answer": {"accuracy": 0.98}},
        system_evidence_ids=["ev-1"],
        execution_time_ms=150,
    )

    summary, metrics = compute_evaluation_summary([task], run, [result])
    assert summary.total_tasks == 1
    assert summary.completed_tasks == 1
    assert summary.failed_tasks == 0
    assert summary.task_success_rate == 1.0
    assert len(metrics) > 0
    metric_names = [m.metric_name for m in metrics]
    assert MetricType.TASK_SUCCESS in metric_names


@pytest.mark.asyncio
async def test_evaluation_service_persistence():
    extraction_mock = MagicMock()
    retrieval_mock = MagicMock()
    synth_mock = MagicMock()
    verif_mock = MagicMock()
    report_mock = MagicMock()

    service = EvaluationService(
        extraction_service=extraction_mock,
        retrieval_service=retrieval_mock,
        synthesis_service=synth_mock,
        verification_service=verif_mock,
        report_service=report_mock,
    )

    config = EvaluationConfig(
        benchmark_version="1.0.0",
        model_profile="fast",
        system_type="direct_llm",
    )

    summary = await service.run_evaluation(config)
    assert summary is not None
    assert summary.total_tasks >= 0

    runs = service.list_runs()
    assert len(runs) == 1
    run = runs[0]
    assert run.run_id == summary.evaluation_run_id

    fetched_run = service.get_run(run.run_id)
    assert fetched_run is not None
    assert fetched_run.run_id == run.run_id

    results = service.get_results(run.run_id)
    assert isinstance(results, list)

    metrics = service.get_metrics(run.run_id)
    assert isinstance(metrics, list)
