from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.agent.factory import get_provider
from packages.evaluation.schemas import (
    BenchmarkTask,
    Difficulty,
    EvaluationConfig,
    EvaluationRun,
    EvaluationSummary,
    TaskCategory,
    TaskResult,
)
from packages.extraction.service import ExtractionService
from packages.retrieval.service import RetrievalService
from packages.synthesis.service import SynthesisService
from packages.verification.report_generator import ReportGenerationService
from packages.verification.verifier import CitationVerificationService


class EvaluationRunner:
    def __init__(
        self,
        extraction_service: ExtractionService,
        retrieval_service: RetrievalService,
        synthesis_service: SynthesisService,
        verification_service: CitationVerificationService,
        report_service: ReportGenerationService,
        config: EvaluationConfig | None = None,
    ):
        self.extraction_service = extraction_service
        self.retrieval_service = retrieval_service
        self.synthesis_service = synthesis_service
        self.verification_service = verification_service
        self.report_service = report_service
        self.config = config or EvaluationConfig()
        self.tasks: list[BenchmarkTask] = []
        self._load_benchmark()

    def _load_benchmark(self) -> None:
        benchmark_path = Path("data/benchmark/gold.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                data = json.load(f)
            for task_data in data.get("tasks", []):
                task = BenchmarkTask(
                    task_id=UUID(task_data["task_id"]),
                    benchmark_version=data.get("benchmark_version", "1.0.0"),
                    category=TaskCategory(task_data["category"]),
                    prompt=task_data["prompt"],
                    paper_ids=[UUID(pid) for pid in task_data.get("paper_ids", [])],
                    gold_answer=task_data["gold_answer"],
                    gold_evidence_ids=task_data.get("gold_evidence_ids", []),
                    difficulty=Difficulty(task_data.get("difficulty", "medium")),
                    tags=task_data.get("tags", []),
                )
                self.tasks.append(task)

    def filter_tasks(
        self,
        categories: list[TaskCategory] | None = None,
        difficulties: list[Difficulty] | None = None,
    ) -> list[BenchmarkTask]:
        filtered = self.tasks
        if categories:
            filtered = [t for t in filtered if t.category in categories]
        if difficulties:
            filtered = [t for t in filtered if t.difficulty in difficulties]
        return filtered

    async def run_evaluation(self, config: EvaluationConfig | None = None) -> EvaluationRun:
        config = config or self.config
        filtered_tasks = self.filter_tasks(config.categories, config.difficulties)

        run = EvaluationRun(
            run_id=uuid.uuid4(),
            benchmark_version=config.benchmark_version,
            model_profile=config.model_profile,
            system_type=config.system_type,
            total_tasks=len(filtered_tasks),
        )

        provider = get_provider(model_profile=config.model_profile)

        for _i, task in enumerate(filtered_tasks):
            start_time = time.perf_counter()
            try:
                result = await self._run_task(task, provider, config)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                TaskResult(
                    result_id=uuid.uuid4(),
                    evaluation_run_id=run.run_id,
                    task_id=task.task_id,
                    system_output=result.get("output", {}),
                    system_evidence_ids=result.get("evidence_ids", []),
                    execution_time_ms=execution_time_ms,
                    trace_events=result.get("trace", []),
                )
            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                TaskResult(
                    result_id=uuid.uuid4(),
                    evaluation_run_id=run.run_id,
                    task_id=task.task_id,
                    system_output={},
                    system_evidence_ids=[],
                    execution_time_ms=execution_time_ms,
                    trace_events=[],
                    error=str(e),
                )

            run.completed_tasks += 1

        run.completed_at = datetime.utcnow()
        run.status = "completed"
        return run

    async def _run_task(
        self,
        task: BenchmarkTask,
        provider: Any,
        config: EvaluationConfig,
    ) -> dict[str, Any]:
        if config.system_type == "direct_llm":
            return await self._run_direct_llm(task, provider)
        elif config.system_type == "static_rag":
            return await self._run_static_rag(task, provider)
        elif config.system_type == "adaptive_agent":
            return await self._run_adaptive_agent(task, provider)
        else:
            raise ValueError(f"Unknown system type: {config.system_type}")

    async def _run_direct_llm(self, task: BenchmarkTask, provider: Any) -> dict[str, Any]:
        system_prompt = f"""You are a research paper analysis expert. Answer the question based on your knowledge.
Task category: {task.category.value}
Difficulty: {task.difficulty.value}"""

        response = await provider.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.prompt},
            ],
            temperature=0.0,
        )

        return {
            "output": {"answer": response.content},
            "evidence_ids": [],
            "trace": [{"step": "direct_llm", "input": task.prompt, "output": response.content}],
        }

    async def _run_static_rag(self, task: BenchmarkTask, provider: Any) -> dict[str, Any]:
        search_result = await self.retrieval_service.search(
            query=task.prompt,
            top_k=10,
        )

        context = "\n".join([f"[{i}] {hit.text[:500]}" for i, hit in enumerate(search_result.hits)])

        system_prompt = f"""You are a research paper analysis expert. Answer using the provided evidence.
Task category: {task.category.value}
Difficulty: {task.difficulty.value}"""

        response = await provider.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {task.prompt}\n\nEvidence:\n{context}\n\nAnswer based on evidence."},
            ],
            temperature=0.0,
        )

        return {
            "output": {"answer": response.content},
            "evidence_ids": [hit.evidence_id for hit in search_result.hits[:5]],
            "trace": [
                {"step": "retrieval", "query": task.prompt, "hits": len(search_result.hits)},
                {"step": "generation", "input": context[:200], "output": response.content[:200]},
            ],
        }

    async def _run_adaptive_agent(self, task: BenchmarkTask, provider: Any) -> dict[str, Any]:
        from packages.synthesis.service import SynthesisRequest
        from packages.verification.schemas import ReportRequest, VerificationRequest

        trace = []
        evidence_ids = []

        if task.category in [TaskCategory.METADATA_EXTRACTION, TaskCategory.METHOD_EXTRACTION, TaskCategory.RESULT_EXTRACTION]:
            for pid in task.paper_ids:
                claims = await self.extraction_service.get_paper_claims(pid)
                trace.append({"step": "extraction", "paper_id": str(pid), "claims_found": len(claims)})

        if task.category in [TaskCategory.COMPARISON, TaskCategory.GAP_ANALYSIS]:
            synth_request = SynthesisRequest(
                project_id=task.paper_ids[0] if task.paper_ids else uuid.uuid4(),
                paper_ids=task.paper_ids,
            )
            synthesis = await self.synthesis_service.run_synthesis(synth_request)
            trace.append({"step": "synthesis", "tables": len(synthesis.comparison_tables), "gaps": len(synthesis.gaps), "conflicts": len(synthesis.conflicts)})
            for table in synthesis.comparison_tables:
                for row in table.rows:
                    for cell in row.cells:
                        evidence_ids.extend(cell.evidence_ids)
            for gap in synthesis.gaps:
                evidence_ids.extend(gap.evidence_ids)

        if task.category == TaskCategory.CITATION_VERIFICATION:
            verify_request = VerificationRequest(
                draft_text=json.dumps(task.gold_answer),
                evidence_ids=evidence_ids,
                paper_ids=task.paper_ids,
            )
            verification = await self.verification_service.verify_draft(verify_request)
            trace.append({"step": "verification", "status": verification.overall_status.value, "coverage": verification.citation_coverage})
            output = {"verification": verification.overall_status.value, "details": verification.atomic_claims}
        else:
            report_request = ReportRequest(
                project_id=task.paper_ids[0] if task.paper_ids else uuid.uuid4(),
                paper_ids=task.paper_ids,
            )
            report = await self.report_service.generate_report(report_request)
            trace.append({"step": "report_generation", "sections": len(report.sections), "citations": len(report.citations)})
            output = {"answer": report.executive_summary, "report_id": str(report.report_id)}

        return {
            "output": output,
            "evidence_ids": evidence_ids,
            "trace": trace,
        }


class MetricCalculator:
    @staticmethod
    def calculate_task_success(gold: dict, predicted: dict) -> float:
        if not gold or not predicted:
            return 0.0
        matches = sum(1 for k, v in gold.items() if k in predicted and predicted[k] == v)
        return matches / len(gold) if gold else 0.0

    @staticmethod
    def calculate_citation_precision(verification_result: dict) -> float:
        total = verification_result.get("total_claims", 0)
        if total == 0:
            return 0.0
        supported = verification_result.get("verified_claims", 0) + verification_result.get("partially_verified_claims", 0)
        return supported / total

    @staticmethod
    def calculate_unsupported_claim_rate(verification_result: dict) -> float:
        total = verification_result.get("total_claims", 0)
        if total == 0:
            return 0.0
        unsupported = verification_result.get("unsupported_claims_count", 0)
        return unsupported / total

    @staticmethod
    def calculate_retrieval_precision_at_5(gold_evidence: list, retrieved_evidence: list) -> float:
        if not gold_evidence:
            return 1.0
        retrieved_set = set(retrieved_evidence[:5])
        gold_set = set(gold_evidence)
        return len(retrieved_set & gold_set) / min(5, len(gold_set))

    @staticmethod
    def calculate_tool_efficiency(task_result: TaskResult, max_allowed_calls: int = 10) -> float:
        calls = len(task_result.trace_events)
        if calls == 0:
            return 1.0
        return min(1.0, max_allowed_calls / calls)

    @staticmethod
    def calculate_trace_completeness(task_result: TaskResult, expected_steps: list[str]) -> float:
        if not expected_steps:
            return 1.0
        actual_steps = {e.get("step") for e in task_result.trace_events}
        expected_set = set(expected_steps)
        return len(actual_steps & expected_set) / len(expected_set)

    @staticmethod
    def calculate_exact_match(gold: Any, predicted: Any) -> float:
        return 1.0 if gold == predicted else 0.0

    @staticmethod
    def calculate_f1_score(gold: dict, predicted: dict) -> float:
        if not gold and not predicted:
            return 1.0
        gold_keys = set(gold.keys())
        pred_keys = set(predicted.keys())
        if not gold_keys and not pred_keys:
            return 1.0
        tp = len(gold_keys & pred_keys)
        fp = len(pred_keys - gold_keys)
        fn = len(gold_keys - pred_keys)
        if tp == 0:
            return 0.0
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        return 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0


async def run_evaluation(
    extraction_service: ExtractionService,
    retrieval_service: RetrievalService,
    synthesis_service: SynthesisService,
    verification_service: CitationVerificationService,
    report_service: ReportGenerationService,
    config: EvaluationConfig | None = None,
) -> EvaluationSummary:
    runner = EvaluationRunner(
        extraction_service=extraction_service,
        retrieval_service=retrieval_service,
        synthesis_service=synthesis_service,
        verification_service=verification_service,
        report_service=report_service,
        config=config,
    )

    run = await runner.run_evaluation(config)

    MetricCalculator()
    summary = EvaluationSummary(
        evaluation_run_id=run.run_id,
        system_type=config.system_type if config else "adaptive_agent",
        model_profile=config.model_profile if config else "balanced",
        benchmark_version=config.benchmark_version if config else "1.0.0",
        total_tasks=run.total_tasks,
        completed_tasks=run.completed_tasks,
        failed_tasks=run.total_tasks - run.completed_tasks,
        task_success_rate=0.0,
        citation_precision=0.0,
        unsupported_claim_rate=0.0,
        retrieval_precision_at_5=0.0,
        tool_efficiency=0.0,
        trace_completeness=1.0,
        avg_execution_time_ms=0.0,
    )

    return summary
