from __future__ import annotations

from typing import Any
from uuid import UUID

from packages.domain.models import Claim, ClaimStatus, EvidenceLink, SupportType
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ClaimRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_claim(
        self,
        paper_id: UUID,
        claim_type: str,
        claim_text: str,
        normalized_value: dict[str, Any],
        confidence: float,
        status: ClaimStatus = ClaimStatus.EXTRACTED,
        created_by_run_id: UUID | None = None,
    ) -> Claim:
        claim = Claim(
            paper_id=paper_id,
            claim_type=claim_type,
            claim_text=claim_text,
            normalized_value_json=normalized_value,
            confidence=confidence,
            status=status,
            created_by_run_id=created_by_run_id,
        )
        self._session.add(claim)
        await self._session.flush()
        return claim

    async def get_by_id(self, claim_id: UUID) -> Claim | None:
        result = await self._session.execute(
            select(Claim)
            .options(selectinload(Claim.evidence_links))
            .where(Claim.id == claim_id)
        )
        return result.scalar_one_or_none()

    async def get_by_paper(
        self,
        paper_id: UUID,
        claim_type: str | None = None,
        status: ClaimStatus | None = None,
    ) -> list[Claim]:
        query = select(Claim).where(Claim.paper_id == paper_id)
        if claim_type:
            query = query.where(Claim.claim_type == claim_type)
        if status:
            query = query.where(Claim.status == status)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_paper_and_type(
        self,
        paper_id: UUID,
        claim_type: str,
    ) -> Claim | None:
        result = await self._session.execute(
            select(Claim)
            .where(Claim.paper_id == paper_id, Claim.claim_type == claim_type)
        )
        return result.scalar_one_or_none()

    async def update_claim(
        self,
        claim_id: UUID,
        claim_text: str | None = None,
        normalized_value: dict[str, Any] | None = None,
        confidence: float | None = None,
        status: ClaimStatus | None = None,
    ) -> Claim | None:
        claim = await self.get_by_id(claim_id)
        if not claim:
            return None

        if claim_text is not None:
            claim.claim_text = claim_text
        if normalized_value is not None:
            claim.normalized_value_json = normalized_value
        if confidence is not None:
            claim.confidence = confidence
        if status is not None:
            claim.status = status

        await self._session.flush()
        return claim

    async def add_evidence_link(
        self,
        claim_id: UUID,
        chunk_id: UUID,
        page_number: int,
        support_type: SupportType = SupportType.SUPPORTS,
        match_score: float = 0.0,
    ) -> EvidenceLink:
        evidence_link = EvidenceLink(
            claim_id=claim_id,
            chunk_id=chunk_id,
            page_number=page_number,
            support_type=support_type,
            match_score=match_score,
        )
        self._session.add(evidence_link)
        await self._session.flush()
        return evidence_link

    async def get_evidence_links(self, claim_id: UUID) -> list[EvidenceLink]:
        result = await self._session.execute(
            select(EvidenceLink).where(EvidenceLink.claim_id == claim_id)
        )
        return list(result.scalars().all())

    async def delete_claim(self, claim_id: UUID) -> bool:
        claim = await self.get_by_id(claim_id)
        if not claim:
            return False
        await self._session.delete(claim)
        await self._session.flush()
        return True

    async def count_by_paper(self, paper_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(Claim.id)).where(Claim.paper_id == paper_id)
        )
        return result.scalar() or 0
