from __future__ import annotations

from uuid import UUID

from packages.evaluation.schemas import (
    EvaluationConfig,
    EvaluationRun,
    EvaluationSummary,
    MetricResult,
    TaskResult,
)
from packages.extraction.service import ExtractionService
from packages.retrieval.service import RetrievalService
from packages.synthesis.service import SynthesisService
from packages.verification.report_generator import ReportGenerationService
from packages.verification.verifier import CitationVerificationService


class EvaluationService:
    def __init__(
        self,
        extraction_service: ExtractionService,
        retrieval_service: RetrievalService,
        synthesis_service: SynthesisService,
        verification_service: CitationVerificationService,
        report_service: ReportGenerationService,
    ):
        self.extraction_service = extraction_service
        self.retrieval_service = retrieval_service
        self.synthesis_service = synthesis_service
        self.verification_service = verification_service
        self.report_service = report_service
        self._runs: dict[UUID, EvaluationRun] = {}
        self._results: dict[UUID, list[TaskResult]] = {}
        self._metrics: dict[UUID, list[MetricResult]] = {}

    async def run_evaluation(self, config: EvaluationConfig | None = None) -> EvaluationSummary:
        from packages.evaluation.runner import run_evaluation as _run_evaluation
        summary = await _run_evaluation(
            extraction_service=self.extraction_service,
            retrieval_service=self.retrieval_service,
            synthesis_service=self.synthesis_service,
            verification_service=self.verification_service,
            report_service=self.report_service,
            config=config,
        )
        return summary

    def get_run(self, run_id: UUID) -> EvaluationRun | None:
        return self._runs.get(run_id)

    def get_results(self, run_id: UUID) -> list[TaskResult]:
        return self._results.get(run_id, [])

    def get_metrics(self, run_id: UUID) -> list[MetricResult]:
        return self._metrics.get(run_id, [])

    def list_runs(self) -> list[EvaluationRun]:
        return list(self._runs.values())


_evaluation_service: EvaluationService | None = None


def get_evaluation_service(
    extraction_service: ExtractionService,
    retrieval_service: RetrievalService,
    synthesis_service: SynthesisService,
    verification_service: CitationVerificationService,
    report_service: ReportGenerationService,
) -> EvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService(
            extraction_service=extraction_service,
            retrieval_service=retrieval_service,
            synthesis_service=synthesis_service,
            verification_service=verification_service,
            report_service=report_service,
        )
    return _evaluation_service
