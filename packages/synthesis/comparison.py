from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any
from uuid import UUID

from packages.extraction.schemas import ClaimType
from packages.synthesis.normalization import get_normalization_service
from packages.synthesis.schemas import (
    ComparisonCell,
    ComparisonRow,
    ComparisonTable,
    ComparisonType,
    Conflict,
    ConflictType,
    NormalizedValue,
)


class ComparisonService:
    def __init__(self):
        self.normalizer = get_normalization_service()

    def build_comparison_table(
        self,
        project_id: UUID,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
        comparison_type: ComparisonType,
    ) -> ComparisonTable:
        rows = []

        if comparison_type == ComparisonType.MODEL:
            rows = self._build_model_comparison(paper_ids, paper_claims)
        elif comparison_type == ComparisonType.DATASET:
            rows = self._build_dataset_comparison(paper_ids, paper_claims)
        elif comparison_type == ComparisonType.METRICS:
            rows = self._build_metrics_comparison(paper_ids, paper_claims)
        elif comparison_type == ComparisonType.PREPROCESSING:
            rows = self._build_preprocessing_comparison(paper_ids, paper_claims)
        elif comparison_type == ComparisonType.RESULTS:
            rows = self._build_results_comparison(paper_ids, paper_claims)
        elif comparison_type == ComparisonType.LIMITATIONS:
            rows = self._build_limitations_comparison(paper_ids, paper_claims)

        return ComparisonTable(
            table_id=uuid.uuid4(),
            project_id=project_id,
            paper_ids=paper_ids,
            comparison_type=comparison_type,
            rows=rows,
        )

    def _build_model_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        attributes = [
            ("name", "Model Name"),
            ("architecture", "Architecture"),
            ("framework", "Framework"),
            ("parameters", "Parameters"),
            ("pretrained", "Pre-trained"),
        ]

        rows = []
        for attr_key, attr_label in attributes:
            cells = []
            for pid in paper_ids:
                claims = paper_claims.get(pid, {}).get(ClaimType.MODEL, [])
                if not claims:
                    cells.append(self._empty_cell(pid, "Unknown"))
                    continue

                claim = claims[0]
                normalized = claim.get("normalized_value", {})
                value = normalized.get(attr_key)
                if value is None:
                    cells.append(self._empty_cell(pid, claim.get("claim_text", "Not reported")))
                    continue

                norm_entity = (
                    self.normalizer.normalize_model(str(value)) if attr_key == "name" else None
                )
                cells.append(
                    ComparisonCell(
                        paper_id=pid,
                        paper_title=claim.get("paper_title", "Unknown"),
                        value=NormalizedValue(
                            value=norm_entity.normalized_value if norm_entity else value,
                            confidence=norm_entity.confidence if norm_entity else 0.8,
                            source_claim_ids=[claim.get("claim_id")]
                            if claim.get("claim_id")
                            else [],
                        ),
                        claim_id=claim.get("claim_id"),
                        evidence_ids=claim.get("evidence_ids", []),
                    )
                )

            rows.append(
                ComparisonRow(
                    attribute=attr_label,
                    attribute_type=ComparisonType.MODEL,
                    cells=cells,
                )
            )

        return rows

    def _build_dataset_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        attributes = [
            ("name", "Dataset Name"),
            ("size", "Size"),
            ("source", "Source"),
            ("splits", "Splits"),
            ("domain", "Domain"),
        ]

        rows = []
        for attr_key, attr_label in attributes:
            cells = []
            for pid in paper_ids:
                claims = paper_claims.get(pid, {}).get(ClaimType.DATASET, [])
                if not claims:
                    cells.append(self._empty_cell(pid, "Unknown"))
                    continue

                claim = claims[0]
                normalized = claim.get("normalized_value", {})
                value = normalized.get(attr_key)

                norm_entity = (
                    self.normalizer.normalize_dataset(str(value))
                    if attr_key == "name" and value
                    else None
                )
                cells.append(
                    ComparisonCell(
                        paper_id=pid,
                        paper_title=claim.get("paper_title", "Unknown"),
                        value=NormalizedValue(
                            value=norm_entity.normalized_value
                            if norm_entity
                            else (value or "Not reported"),
                            confidence=norm_entity.confidence if norm_entity else 0.8,
                            source_claim_ids=[claim.get("claim_id")]
                            if claim.get("claim_id")
                            else [],
                        ),
                        claim_id=claim.get("claim_id"),
                        evidence_ids=claim.get("evidence_ids", []),
                    )
                )

            rows.append(
                ComparisonRow(
                    attribute=attr_label,
                    attribute_type=ComparisonType.DATASET,
                    cells=cells,
                )
            )

        return rows

    def _build_metrics_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        all_metrics = set()
        for pid in paper_ids:
            claims = paper_claims.get(pid, {}).get(ClaimType.METRICS, [])
            for claim in claims:
                normalized = claim.get("normalized_value", {})
                metrics = normalized.get("metrics", [])
                for m in metrics:
                    if isinstance(m, str):
                        all_metrics.add(m)
                    elif isinstance(m, dict):
                        all_metrics.add(m.get("name", ""))

        rows = []
        for metric in sorted(all_metrics):
            if not metric:
                continue
            cells = []
            norm_metric = self.normalizer.normalize_metric(metric)
            for pid in paper_ids:
                claims = paper_claims.get(pid, {}).get(ClaimType.METRICS, [])
                found = False
                for claim in claims:
                    normalized = claim.get("normalized_value", {})
                    metrics = normalized.get("metrics", [])
                    for m in metrics:
                        m_name = m if isinstance(m, str) else m.get("name", "")
                        if (
                            self.normalizer.normalize_metric(m_name).normalized_value
                            == norm_metric.normalized_value
                        ):
                            cells.append(
                                ComparisonCell(
                                    paper_id=pid,
                                    paper_title=claim.get("paper_title", "Unknown"),
                                    value=NormalizedValue(
                                        value=norm_metric.normalized_value,
                                        confidence=0.8,
                                        source_claim_ids=[claim.get("claim_id")]
                                        if claim.get("claim_id")
                                        else [],
                                    ),
                                    claim_id=claim.get("claim_id"),
                                    evidence_ids=claim.get("evidence_ids", []),
                                )
                            )
                            found = True
                            break
                    if found:
                        break

                if not found:
                    cells.append(self._empty_cell(pid, "Not reported"))

            rows.append(
                ComparisonRow(
                    attribute=norm_metric.normalized_value,
                    attribute_type=ComparisonType.METRICS,
                    cells=cells,
                )
            )

        return rows

    def _build_preprocessing_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        attributes = [
            ("steps", "Preprocessing Steps"),
            ("tools", "Tools"),
            ("tokenization", "Tokenization"),
        ]

        rows = []
        for attr_key, attr_label in attributes:
            cells = []
            for pid in paper_ids:
                claims = paper_claims.get(pid, {}).get(ClaimType.PREPROCESSING, [])
                if not claims:
                    cells.append(self._empty_cell(pid, "Not reported"))
                    continue

                claim = claims[0]
                normalized = claim.get("normalized_value", {})
                value = normalized.get(attr_key, "Not reported")

                cells.append(
                    ComparisonCell(
                        paper_id=pid,
                        paper_title=claim.get("paper_title", "Unknown"),
                        value=NormalizedValue(
                            value=value,
                            confidence=0.8,
                            source_claim_ids=[claim.get("claim_id")]
                            if claim.get("claim_id")
                            else [],
                        ),
                        claim_id=claim.get("claim_id"),
                        evidence_ids=claim.get("evidence_ids", []),
                    )
                )

            rows.append(
                ComparisonRow(
                    attribute=attr_label,
                    attribute_type=ComparisonType.PREPROCESSING,
                    cells=cells,
                )
            )

        return rows

    def _flatten_metric_results(self, metric_results: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for metric, result in metric_results.items():
            if isinstance(result, dict) and "value" in result:
                flat[metric] = result.get("value")
            elif isinstance(result, dict):
                if not result:
                    flat[metric] = result
                else:
                    for sub_k, sub_v in result.items():
                        flat[f"{metric} {sub_k}"] = sub_v
            else:
                flat[metric] = result
        return flat

    def _extract_numeric(self, result: Any) -> float | None:
        try:
            if isinstance(result, dict):
                if "value" in result:
                    v = result.get("value")
                    return float(v) if v is not None else None
                for v in result.values():
                    try:
                        return float(v)  # type: ignore[arg-type]
                    except (ValueError, TypeError):
                        continue
                return None
            if result is None:
                return None
            return float(result)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None

    def _build_results_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        all_metrics: set[str] = set()
        for pid in paper_ids:
            claims = paper_claims.get(pid, {}).get(ClaimType.RESULTS, [])
            for claim in claims:
                normalized = claim.get("normalized_value", {})
                metric_results = normalized.get("metric_results", {})
                if isinstance(metric_results, dict):
                    for m in self._flatten_metric_results(metric_results).keys():
                        all_metrics.add(m)

        rows = []
        for metric in sorted(all_metrics):
            cells = []
            for pid in paper_ids:
                claims = paper_claims.get(pid, {}).get(ClaimType.RESULTS, [])
                found = False
                for claim in claims:
                    normalized = claim.get("normalized_value", {})
                    metric_results = normalized.get("metric_results", {})
                    flat = self._flatten_metric_results(
                        metric_results if isinstance(metric_results, dict) else {}
                    )
                    if metric in flat:
                        result = flat[metric]
                        cells.append(
                            ComparisonCell(
                                paper_id=pid,
                                paper_title=claim.get("paper_title", "Unknown"),
                                value=NormalizedValue(
                                    value=result,
                                    confidence=0.8,
                                    source_claim_ids=[claim.get("claim_id")]
                                    if claim.get("claim_id")
                                    else [],
                                ),
                                claim_id=claim.get("claim_id"),
                                evidence_ids=claim.get("evidence_ids", []),
                            )
                        )
                        found = True
                        break

                if not found:
                    cells.append(self._empty_cell(pid, "Not reported"))

            rows.append(
                ComparisonRow(
                    attribute=metric,
                    attribute_type=ComparisonType.RESULTS,
                    cells=cells,
                )
            )

        return rows

    def _build_limitations_comparison(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[ComparisonRow]:
        categories: dict[str, list[tuple[UUID, dict[str, Any]]]] = {}
        for pid in paper_ids:
            claims = paper_claims.get(pid, {}).get(ClaimType.LIMITATIONS, [])
            for claim in claims:
                normalized = claim.get("normalized_value", {})
                if not isinstance(normalized, dict):
                    continue
                key = normalized.get("category", "general") or "general"
                key = str(key).strip().lower() or "general"
                categories.setdefault(key, []).append((pid, claim))

        rows = []
        for key in sorted(categories.keys()):
            cells = []
            by_pid: dict[UUID, dict[str, Any]] = {}
            for pid, claim in categories[key]:
                if pid not in by_pid:
                    by_pid[pid] = claim
            for pid in paper_ids:
                claim = by_pid.get(pid)
                if claim is not None:
                    normalized = claim.get("normalized_value", {})
                    cells.append(
                        ComparisonCell(
                            paper_id=pid,
                            paper_title=claim.get("paper_title", "Unknown"),
                            value=NormalizedValue(
                                value=normalized.get("limitation_text", "Reported"),
                                confidence=0.8,
                                source_claim_ids=[claim.get("claim_id")]
                                if claim.get("claim_id")
                                else [],
                            ),
                            claim_id=claim.get("claim_id"),
                            evidence_ids=claim.get("evidence_ids", []),
                        )
                    )
                else:
                    first_title = self._first_title_for_pid(paper_ids, paper_claims, pid)
                    cells.append(self._empty_cell(pid, "Not mentioned", paper_title=first_title))

            rows.append(
                ComparisonRow(
                    attribute=f"Limitation: {key}",
                    attribute_type=ComparisonType.LIMITATIONS,
                    cells=cells,
                )
            )

        return rows

    def _first_title_for_pid(
        self,
        paper_ids: list[UUID],
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
        pid: UUID,
    ) -> str:
        for claims_by_type in paper_claims.get(pid, {}).values():
            for claim in claims_by_type:
                title = claim.get("paper_title")
                if isinstance(title, str) and title:
                    return title
        return "Unknown"

    def _empty_cell(
        self, paper_id: UUID, value: str, paper_title: str = "Unknown"
    ) -> ComparisonCell:
        return ComparisonCell(
            paper_id=paper_id,
            paper_title=paper_title,
            value=NormalizedValue(
                value=value,
                confidence=0.0,
            ),
            evidence_ids=[],
        )

    def detect_conflicts(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Conflict]:
        conflicts = []

        conflicts.extend(self._detect_preprocessing_conflicts(paper_claims))
        conflicts.extend(self._detect_metric_definition_conflicts(paper_claims))
        conflicts.extend(self._detect_result_conflicts(paper_claims))
        conflicts.extend(self._detect_model_config_conflicts(paper_claims))

        return conflicts

    def _detect_preprocessing_conflicts(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Conflict]:
        conflicts = []
        preprocessing_by_paper = {}

        for pid, claims_by_type in paper_claims.items():
            prep_claims = claims_by_type.get(ClaimType.PREPROCESSING, [])
            if prep_claims:
                normalized = prep_claims[0].get("normalized_value", {})
                steps = normalized.get("steps", [])
                preprocessing_by_paper[pid] = {str(s).lower() for s in steps}

        papers = list(preprocessing_by_paper.keys())
        for i, pid1 in enumerate(papers):
            for pid2 in papers[i + 1 :]:
                steps1 = preprocessing_by_paper[pid1]
                steps2 = preprocessing_by_paper[pid2]
                if steps1 and steps2 and steps1 != steps2:
                    diff1 = steps1 - steps2
                    diff2 = steps2 - steps1
                    if diff1 or diff2:
                        conflicts.append(
                            Conflict(
                                conflict_id=uuid.uuid4(),
                                conflict_type=ConflictType.INCOMPATIBLE_PREPROCESSING,
                                paper_ids=[pid1, pid2],
                                description="Different preprocessing steps between papers",
                                details={
                                    "paper1_steps": list(steps1),
                                    "paper2_steps": list(steps2),
                                    "paper1_only": list(diff1),
                                    "paper2_only": list(diff2),
                                },
                                severity="medium",
                            )
                        )

        return conflicts

    def _detect_metric_definition_conflicts(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Conflict]:
        conflicts = []
        metric_defs = {}

        for pid, claims_by_type in paper_claims.items():
            metric_claims = claims_by_type.get(ClaimType.METRICS, [])
            for claim in metric_claims:
                normalized = claim.get("normalized_value", {})
                defs = normalized.get("metric_definitions", {})
                for metric, definition in defs.items():
                    norm_metric = self.normalizer.normalize_metric(metric)
                    key = norm_metric.normalized_value
                    if key not in metric_defs:
                        metric_defs[key] = {}
                    metric_defs[key][pid] = definition

        for metric, defs_by_paper in metric_defs.items():
            if len(defs_by_paper) > 1:
                import json

                def _freeze(v: Any) -> str:
                    try:
                        return json.dumps(v, sort_keys=True, default=str)
                    except Exception:
                        return str(v)

                unique = {_freeze(v) for v in defs_by_paper.values()}
                if len(unique) > 1:
                    conflicts.append(
                        Conflict(
                            conflict_id=uuid.uuid4(),
                            conflict_type=ConflictType.DIFFERENT_METRIC_DEFINITIONS,
                            paper_ids=list(defs_by_paper.keys()),
                            description=f"Different definitions for metric '{metric}'",
                            details={"definitions": defs_by_paper},
                            severity="high",
                        )
                    )

        return conflicts

    def _detect_result_conflicts(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Conflict]:
        conflicts = []
        result_by_metric: dict[str, dict[UUID, Any]] = defaultdict(dict)

        for pid, claims_by_type in paper_claims.items():
            result_claims = claims_by_type.get(ClaimType.RESULTS, [])
            for claim in result_claims:
                normalized = claim.get("normalized_value", {})
                metric_results = normalized.get("metric_results", {})
                if not isinstance(metric_results, dict):
                    continue
                for metric, result in self._flatten_metric_results(metric_results).items():
                    result_by_metric[metric][pid] = result

        for metric, results_by_paper in result_by_metric.items():
            if len(results_by_paper) > 1:
                numeric_results: dict[UUID, float] = {}
                for pid, result in results_by_paper.items():
                    val = self._extract_numeric(result)
                    if val is not None:
                        numeric_results[pid] = val

                if len(numeric_results) > 1:
                    values = list(numeric_results.values())
                    if max(values) - min(values) > 0.1:
                        conflicts.append(
                            Conflict(
                                conflict_id=uuid.uuid4(),
                                conflict_type=ConflictType.CONFLICTING_RESULTS,
                                paper_ids=list(numeric_results.keys()),
                                description=f"Significantly different results for metric '{metric}'",
                                details={
                                    "results": numeric_results,
                                    "range": max(values) - min(values),
                                },
                                severity="high",
                            )
                        )

        return conflicts

    def _detect_model_config_conflicts(
        self,
        paper_claims: dict[UUID, dict[ClaimType, list[dict[str, Any]]]],
    ) -> list[Conflict]:
        conflicts = []
        model_configs = {}

        for pid, claims_by_type in paper_claims.items():
            model_claims = claims_by_type.get(ClaimType.MODEL, [])
            for claim in model_claims:
                normalized = claim.get("normalized_value", {})
                config = {
                    "name": normalized.get("name"),
                    "architecture": normalized.get("architecture"),
                    "framework": normalized.get("framework"),
                }
                model_configs[pid] = config

        papers = list(model_configs.keys())
        for i, pid1 in enumerate(papers):
            for pid2 in papers[i + 1 :]:
                config1 = model_configs[pid1]
                config2 = model_configs[pid2]
                if config1.get("name") and config2.get("name"):
                    norm1 = self.normalizer.normalize_model(config1["name"])
                    norm2 = self.normalizer.normalize_model(config2["name"])
                    if norm1.normalized_value == norm2.normalized_value:
                        if config1.get("framework") != config2.get("framework"):
                            conflicts.append(
                                Conflict(
                                    conflict_id=uuid.uuid4(),
                                    conflict_type=ConflictType.INCONSISTENT_MODEL_CONFIG,
                                    paper_ids=[pid1, pid2],
                                    description=f"Same model '{norm1.normalized_value}' with different frameworks",
                                    details={
                                        "framework1": config1.get("framework"),
                                        "framework2": config2.get("framework"),
                                    },
                                    severity="medium",
                                )
                            )

        return conflicts


_comparison_service: ComparisonService | None = None


def get_comparison_service() -> ComparisonService:
    global _comparison_service
    if _comparison_service is None:
        _comparison_service = ComparisonService()
    return _comparison_service
