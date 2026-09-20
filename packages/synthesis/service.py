from __future__ import annotations

import uuid
from typing import Any

from packages.extraction.schemas import ClaimType
from packages.extraction.service import ExtractionService
from packages.synthesis.comparison import ComparisonService
from packages.synthesis.gap_analysis import GapAnalysisService
from packages.synthesis.normalization import NormalizationService
from packages.synthesis.schemas import (
    ComparisonType,
    SynthesisRequest,
    SynthesisResponse,
)


class SynthesisService:
    def __init__(
        self,
        extraction_service: ExtractionService,
        comparison_service: ComparisonService | None = None,
        gap_service: GapAnalysisService | None = None,
        normalization_service: NormalizationService | None = None,
    ):
        self.extraction_service = extraction_service
        self.comparison_service = comparison_service or ComparisonService()
        self.gap_service = gap_service or GapAnalysisService()
        self.normalization_service = normalization_service or NormalizationService()

    async def run_synthesis(self, request: SynthesisRequest) -> SynthesisResponse:
        paper_claims = {}
        for pid in request.paper_ids:
            claims = await self.extraction_service.get_paper_claims(pid)
            paper_claims[pid] = self._organize_claims(claims)

        comparison_tables = []
        comparison_types = request.comparison_types or list(ComparisonType)

        for comp_type in comparison_types:
            table = self.comparison_service.build_comparison_table(
                project_id=request.project_id,
                paper_ids=request.paper_ids,
                paper_claims=paper_claims,
                comparison_type=comp_type,
            )
            comparison_tables.append(table)

        conflicts = []
        if request.include_conflicts:
            conflicts = self.comparison_service.detect_conflicts(paper_claims)

        gaps = []
        if request.include_gaps:
            gaps = self.gap_service.analyze_gaps(paper_claims)

        return SynthesisResponse(
            synthesis_id=uuid.uuid4(),
            project_id=request.project_id,
            comparison_tables=comparison_tables,
            conflicts=conflicts,
            gaps=gaps,
        )

    def _organize_claims(self, claims: list) -> dict[ClaimType, list[dict[str, Any]]]:
        organized = {}
        for claim in claims:
            claim_type = ClaimType(claim.claim_type)
            if claim_type not in organized:
                organized[claim_type] = []
            organized[claim_type].append({
                "claim_id": claim.claim_id,
                "claim_type": claim.claim_type,
                "claim_text": claim.claim_text,
                "normalized_value": claim.normalized_value,
                "confidence": claim.confidence,
                "status": claim.status,
                "evidence_ids": claim.evidence_ids,
                "paper_title": getattr(claim, "paper_title", "Unknown"),
            })
        return organized


_synthesis_service: SynthesisService | None = None


def get_synthesis_service(extraction_service):
    global _synthesis_service
    if _synthesis_service is None:
        _synthesis_service = SynthesisService(extraction_service=extraction_service)
    return _synthesis_service
