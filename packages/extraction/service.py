from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from packages.agent.factory import get_provider
from packages.extraction.extractor import extract_all_claims
from packages.extraction.repository import ClaimRepository
from packages.extraction.schemas import (
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    ClaimStatus,
    ClaimType,
    EvidenceLinkRequest,
    EvidenceLinkResponse,
    ExtractionJobStatus,
)
from packages.ingestion.schemas import ParsedPaper
from sqlalchemy.ext.asyncio import AsyncSession


class ExtractionService:
    def __init__(
        self,
        session: AsyncSession,
        provider_name: str | None = None,
        repo: ClaimRepository | None = None,
    ):
        self._session = session
        self._provider = get_provider(provider_name)
        self._repo = repo or ClaimRepository(session)
        self._jobs: dict[UUID, ExtractionJobStatus] = {}

    async def extract_claims(
        self,
        paper_id: UUID,
        parsed_paper: ParsedPaper,
        request: ClaimExtractionRequest | None = None,
    ) -> list[ClaimExtractionResponse]:
        if request is None:
            request = ClaimExtractionRequest(paper_id=paper_id)

        job_id = uuid.uuid4()
        claim_types = request.claim_types or list(ClaimType)

        self._jobs[job_id] = ExtractionJobStatus(
            job_id=job_id,
            paper_id=paper_id,
            status="processing",
            progress=0.0,
            current_claim_type=None,
            claims_extracted=0,
            started_at=datetime.utcnow(),
        )

        paper_text = "\n\n".join([page.text for page in parsed_paper.pages])

        self._jobs[job_id].progress = 0.1

        results = await extract_all_claims(
            provider=self._provider,
            paper_text=paper_text,
            claim_types=claim_types,
        )

        responses = []
        total = len(claim_types)
        for i, (claim_type, model_response) in enumerate(results.items()):
            self._jobs[job_id].current_claim_type = claim_type.value
            self._jobs[job_id].progress = 0.1 + (0.8 * (i / total))

            if model_response.finish_reason == "error":
                continue

            try:
                import json
                normalized = json.loads(model_response.content)
            except json.JSONDecodeError:
                normalized = {"raw": model_response.content}

            claim = await self._repo.create_claim(
                paper_id=paper_id,
                claim_type=claim_type.value,
                claim_text=self._summarize_claim(normalized, claim_type),
                normalized_value=normalized,
                confidence=0.8,
                status=ClaimStatus.EXTRACTED,
            )

            response = ClaimExtractionResponse(
                claim_id=claim.id,
                claim_type=claim_type,
                claim_text=self._summarize_claim(normalized, claim_type),
                normalized_value=normalized,
                confidence=0.8,
                status=ClaimStatus.EXTRACTED,
            )
            responses.append(response)

        self._jobs[job_id].progress = 1.0
        self._jobs[job_id].status = "completed"
        self._jobs[job_id].claims_extracted = len(responses)
        self._jobs[job_id].completed_at = datetime.utcnow()

        return responses

    def _summarize_claim(self, normalized: dict[str, Any], claim_type: ClaimType) -> str:
        if claim_type == ClaimType.RESEARCH_PROBLEM:
            return normalized.get("problem_statement", "Research problem extracted")
        elif claim_type == ClaimType.DATASET:
            return normalized.get("name", "Dataset information extracted")
        elif claim_type == ClaimType.MODEL:
            return normalized.get("name", "Model information extracted")
        elif claim_type == ClaimType.RESULTS:
            return "Results extracted"
        elif claim_type == ClaimType.LIMITATIONS:
            return normalized.get("limitation_text", "Limitation extracted")
        elif claim_type == ClaimType.FUTURE_WORK:
            return normalized.get("suggestion", "Future work suggestion extracted")
        elif claim_type == ClaimType.METRICS:
            return "Metrics extracted"
        elif claim_type == ClaimType.PREPROCESSING:
            return "Preprocessing steps extracted"
        return f"{claim_type.value} extracted"

    async def link_evidence(self, request: EvidenceLinkRequest) -> EvidenceLinkResponse:
        evidence_link = await self._repo.add_evidence_link(
            claim_id=request.claim_id,
            chunk_id=request.chunk_id,
            page_number=request.page_number,
            support_type=request.support_type,
            match_score=request.match_score,
        )

        return EvidenceLinkResponse(
            evidence_id=f"ev_{evidence_link.id}",
            claim_id=evidence_link.claim_id,
            chunk_id=evidence_link.chunk_id,
            page_number=evidence_link.page_number,
            support_type=evidence_link.support_type,
            match_score=evidence_link.match_score,
        )

    async def get_claim(self, claim_id: UUID) -> ClaimExtractionResponse | None:
        claim = await self._repo.get_by_id(claim_id)
        if not claim:
            return None

        return ClaimExtractionResponse(
            claim_id=claim.id,
            claim_type=ClaimType(claim.claim_type),
            claim_text=claim.claim_text,
            normalized_value=claim.normalized_value_json,
            confidence=claim.confidence,
            status=claim.status,
            evidence_ids=[f"ev_{el.id}" for el in claim.evidence_links],
        )

    async def get_paper_claims(self, paper_id: UUID) -> list[ClaimExtractionResponse]:
        claims = await self._repo.get_by_paper(paper_id)

        return [
            ClaimExtractionResponse(
                claim_id=c.id,
                claim_type=ClaimType(c.claim_type),
                claim_text=c.claim_text,
                normalized_value=c.normalized_value_json,
                confidence=c.confidence,
                status=c.status,
                evidence_ids=[f"ev_{el.id}" for el in c.evidence_links],
            )
            for c in claims
        ]

    def get_job_status(self, job_id: UUID) -> ExtractionJobStatus | None:
        return self._jobs.get(job_id)


def get_extraction_service(session) -> ExtractionService:
    return ExtractionService(session)
