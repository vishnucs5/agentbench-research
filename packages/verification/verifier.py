from __future__ import annotations

import json
import re
import uuid

from packages.agent.factory import get_provider
from packages.extraction.service import ExtractionService
from packages.retrieval.service import RetrievalService
from packages.verification.schemas import (
    AtomicClaim,
    AtomicClaimStatus,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)


class CitationVerificationService:
    def __init__(
        self,
        extraction_service: ExtractionService,
        retrieval_service: RetrievalService,
    ):
        self.extraction_service = extraction_service
        self.retrieval_service = retrieval_service
        self.provider = get_provider("mock")

    def split_into_atomic_claims(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        atomic_claims = []
        for sent in sentences:
            sent = sent.strip()
            if sent and len(sent) > 10:
                atomic_claims.append(sent)
        return atomic_claims

    def classify_claim_type(self, claim: str) -> str:
        opinion_markers = [
            "i think", "i believe", "in my opinion", "it seems", "appears to",
            "suggests that", "may indicate", "could be", "likely", "probably",
            "should", "would be better", "recommend", "propose"
        ]
        claim_lower = claim.lower()
        for marker in opinion_markers:
            if marker in claim_lower:
                return "opinion"
        if re.search(r"\d+(\.\d+)?\s*%", claim) or re.search(r"p\s*[<=>]\s*0\.\d+", claim):
            return "factual"
        if re.search(r"(accuracy|f1|precision|recall|auc)\s*[=:]\s*\d", claim, re.I):
            return "factual"
        return "factual"

    async def verify_claim_against_evidence(
        self,
        claim: str,
        evidence_texts: list[str],
        strict_mode: bool = False,
    ) -> AtomicClaim:
        claim_id = str(uuid.uuid4())
        claim_type = self.classify_claim_type(claim)

        if claim_type == "opinion":
            return AtomicClaim(
                claim_id=claim_id,
                claim_text=claim,
                claim_type="opinion",
                status=AtomicClaimStatus.OPINION,
                confidence=0.9,
                rationale="Classified as opinion based on language markers",
            )

        system_prompt = """You are a citation verification expert. Given a claim and evidence texts, determine if the claim is supported, partially supported, unsupported, or contradicted by the evidence.

Return a JSON object with:
- status: "verified" | "partially_verified" | "unsupported" | "contradicted"
- confidence: 0.0-1.0
- supporting_evidence: list of evidence indices that support
- contradicting_evidence: list of evidence indices that contradict
- rationale: brief explanation"""

        user_prompt = f"""Claim: {claim}

Evidence texts:
{chr(10).join(f"[{i}] {text[:500]}" for i, text in enumerate(evidence_texts))}

Verify this claim against the evidence."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.provider.complete(
                messages=messages,
                temperature=0.0,
                max_tokens=1000,
            )
            result = json.loads(response.content)
        except Exception as e:
            result = {
                "status": "unsupported",
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "rationale": f"Verification failed: {str(e)}",
            }

        status = AtomicClaimStatus(result.get("status", "unsupported"))
        confidence = result.get("confidence", 0.0)
        supporting = result.get("supporting_evidence", [])
        contradicting = result.get("contradicting_evidence", [])
        rationale = result.get("rationale", "")

        return AtomicClaim(
            claim_id=claim_id,
            claim_text=claim,
            claim_type=claim_type,
            status=status,
            supporting_evidence=[evidence_texts[i] for i in supporting if i < len(evidence_texts)],
            contradicting_evidence=[evidence_texts[i] for i in contradicting if i < len(evidence_texts)],
            confidence=confidence,
            rationale=rationale,
        )

    async def verify_draft(self, request: VerificationRequest) -> VerificationResult:
        atomic_claims_text = self.split_into_atomic_claims(request.draft_text)
        evidence_texts = []

        if request.evidence_ids:
            for eid in request.evidence_ids:
                evidence_texts.append(f"Evidence {eid}: [retrieved text]")

        atomic_claims = []
        for claim_text in atomic_claims_text:
            claim_result = await self.verify_claim_against_evidence(
                claim_text, evidence_texts, request.strict_mode
            )
            atomic_claims.append(claim_result)

        verified = sum(1 for c in atomic_claims if c.status == AtomicClaimStatus.VERIFIED)
        partially = sum(1 for c in atomic_claims if c.status == AtomicClaimStatus.PARTIALLY_VERIFIED)
        unsupported = sum(1 for c in atomic_claims if c.status == AtomicClaimStatus.UNSUPPORTED)
        opinion = sum(1 for c in atomic_claims if c.status == AtomicClaimStatus.OPINION)
        contradicted = sum(1 for c in atomic_claims if c.status == AtomicClaimStatus.CONTRADICTED)

        total = len(atomic_claims)
        citation_coverage = (verified + partially) / total if total > 0 else 0.0

        if unsupported + contradicted > 0:
            overall = VerificationStatus.UNSUPPORTED
        elif partially > 0:
            overall = VerificationStatus.PARTIALLY_SUPPORTED
        elif opinion == total:
            overall = VerificationStatus.OPINION
        else:
            overall = VerificationStatus.SUPPORTED

        unsupported_texts = [c.claim_text for c in atomic_claims if c.status in (AtomicClaimStatus.UNSUPPORTED, AtomicClaimStatus.CONTRADICTED)]

        return VerificationResult(
            overall_status=overall,
            atomic_claims=atomic_claims,
            unsupported_claims=unsupported_texts,
            citation_coverage=citation_coverage,
            total_claims=total,
            verified_claims=verified,
            partially_verified_claims=partially,
            unsupported_claims_count=unsupported + contradicted,
            opinion_claims=opinion,
            details={
                "strict_mode": request.strict_mode,
                "evidence_count": len(evidence_texts),
            },
        )


_verification_service: CitationVerificationService | None = None


def get_citation_verification_service(extraction_service, retrieval_service):
    global _verification_service
    if _verification_service is None:
        _verification_service = CitationVerificationService(extraction_service, retrieval_service)
    return _verification_service
