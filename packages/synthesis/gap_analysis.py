from __future__ import annotations

import uuid
from collections import Counter
from typing import Any
from uuid import UUID

from packages.extraction.schemas import ClaimType
from packages.synthesis.schemas import Gap, GapType


class GapAnalysisService:
    def __init__(self):
        self.min_frequency = 2

    def analyze_gaps(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Gap]:
        gaps = []

        gaps.extend(self._find_repeated_limitations(paper_claims))
        gaps.extend(self._find_missing_evaluations(paper_claims))
        gaps.extend(self._find_unexplored_approaches(paper_claims))
        gaps.extend(self._find_data_gaps(paper_claims))

        return gaps

    def _find_repeated_limitations(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Gap]:
        gaps = []
        limitation_texts = []

        for pid, claims_by_type in paper_claims.items():
            lim_claims = claims_by_type.get(ClaimType.LIMITATIONS, [])
            for claim in lim_claims:
                normalized = claim.get("normalized_value", {})
                lim_text = normalized.get("limitation_text", "")
                if lim_text:
                    limitation_texts.append(
                        {
                            "text": lim_text,
                            "paper_id": pid,
                            "claim_id": claim.get("claim_id"),
                            "evidence_ids": claim.get("evidence_ids", []),
                        }
                    )

        if not limitation_texts:
            return gaps

        texts = [lt["text"].lower() for lt in limitation_texts]
        words = []
        for text in texts:
            words.extend([w for w in text.split() if len(w) > 4])

        word_counts = Counter(words)
        repeated_words = {w: c for w, c in word_counts.items() if c >= self.min_frequency}

        for word in sorted(repeated_words.keys()):
            related = [lt for lt in limitation_texts if word in lt["text"].lower()]
            paper_ids = sorted({lt["paper_id"] for lt in related}, key=str)
            frequency = len(paper_ids)
            if frequency < self.min_frequency:
                continue
            gaps.append(
                Gap(
                    gap_id=uuid.uuid4(),
                    gap_type=GapType.REPEATED_LIMITATION,
                    paper_ids=list(paper_ids),
                    description=f"Repeated limitation across papers: '{word}'",
                    evidence_ids=[eid for lt in related for eid in lt["evidence_ids"]],
                    frequency=frequency,
                    severity="high" if frequency >= 3 else "medium",
                )
            )

        return gaps

    def _find_missing_evaluations(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Gap]:
        from packages.synthesis.normalization import normalize_metric_name

        gaps: list[Gap] = []
        all_metrics: set[str] = set()

        for _pid, claims_by_type in paper_claims.items():
            metric_claims = claims_by_type.get(ClaimType.METRICS, [])
            for claim in metric_claims:
                normalized = claim.get("normalized_value", {})
                metrics = normalized.get("metrics", [])
                for m in metrics:
                    m_name = m if isinstance(m, str) else m.get("name", "")
                    if m_name:
                        all_metrics.add(normalize_metric_name(str(m_name)).normalized_value)

        for pid, claims_by_type in paper_claims.items():
            result_claims = claims_by_type.get(ClaimType.RESULTS, [])
            reported_metrics: set[str] = set()
            for claim in result_claims:
                normalized = claim.get("normalized_value", {})
                metric_results = normalized.get("metric_results", {})
                if not isinstance(metric_results, dict):
                    continue
                for m in metric_results:
                    reported_metrics.add(normalize_metric_name(str(m)).normalized_value)

            missing = all_metrics - reported_metrics
            if missing:
                gaps.append(
                    Gap(
                        gap_id=uuid.uuid4(),
                        gap_type=GapType.MISSING_EVALUATION,
                        paper_ids=[pid],
                        description=f"Paper does not report results for metrics: {', '.join(sorted(missing))}",
                        frequency=len(missing),
                        severity="medium",
                    )
                )

        return gaps

    def _find_unexplored_approaches(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Gap]:
        gaps = []
        all_models = set()
        all_datasets = set()

        for _pid, claims_by_type in paper_claims.items():
            model_claims = claims_by_type.get(ClaimType.MODEL, [])
            for claim in model_claims:
                normalized = claim.get("normalized_value", {})
                name = normalized.get("name", "")
                if name:
                    all_models.add(name.lower().strip())

            dataset_claims = claims_by_type.get(ClaimType.DATASET, [])
            for claim in dataset_claims:
                normalized = claim.get("normalized_value", {})
                name = normalized.get("name", "")
                if name:
                    all_datasets.add(name.lower().strip())
                    all_datasets.add(name.lower().strip())

        model_dataset_pairs = set()
        for _pid, claims_by_type in paper_claims.items():
            model_claims = claims_by_type.get(ClaimType.MODEL, [])
            dataset_claims = claims_by_type.get(ClaimType.DATASET, [])
            models = {
                c.get("normalized_value", {}).get("name", "").lower().strip()
                for c in model_claims
                if c.get("normalized_value", {}).get("name")
            }
            datasets = {
                c.get("normalized_value", {}).get("name", "").lower().strip()
                for c in dataset_claims
                if c.get("normalized_value", {}).get("name")
            }
            for m in models:
                for d in datasets:
                    model_dataset_pairs.add((m, d))

        unexplored = []
        for model in all_models:
            for dataset in all_datasets:
                if (model, dataset) not in model_dataset_pairs:
                    unexplored.append((model, dataset))

        if unexplored:
            gaps.append(
                Gap(
                    gap_id=uuid.uuid4(),
                    gap_type=GapType.UNEXPLORED_APPROACH,
                    paper_ids=list(paper_claims.keys()),
                    description=f"Unexplored model-dataset combinations: {len(unexplored)} pairs (e.g., {unexplored[:3]})",
                    frequency=len(unexplored),
                    severity="medium",
                )
            )

        return gaps

    def _find_data_gaps(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Gap]:
        gaps = []

        has_preprocessing = set()
        has_results = set()

        for pid, claims_by_type in paper_claims.items():
            if claims_by_type.get(ClaimType.PREPROCESSING):
                has_preprocessing.add(pid)
            if claims_by_type.get(ClaimType.RESULTS):
                has_results.add(pid)

        all_papers = set(paper_claims.keys())
        missing_preprocessing = all_papers - has_preprocessing
        missing_results = all_papers - has_results

        for pid in missing_preprocessing:
            gaps.append(
                Gap(
                    gap_id=uuid.uuid4(),
                    gap_type=GapType.DATA_GAP,
                    paper_ids=[pid],
                    description="Paper does not report preprocessing steps",
                    frequency=1,
                    severity="medium",
                )
            )

        for pid in missing_results:
            gaps.append(
                Gap(
                    gap_id=uuid.uuid4(),
                    gap_type=GapType.DATA_GAP,
                    paper_ids=[pid],
                    description="Paper does not report results",
                    frequency=1,
                    severity="high",
                )
            )

        return gaps


_gap_analysis_service: GapAnalysisService | None = None


def get_gap_analysis_service() -> GapAnalysisService:
    global _gap_analysis_service
    if _gap_analysis_service is None:
        _gap_analysis_service = GapAnalysisService()
    return _gap_analysis_service
