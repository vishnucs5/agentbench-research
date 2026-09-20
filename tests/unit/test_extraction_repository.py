from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from packages.domain.models import Claim, ClaimStatus, EvidenceLink, SupportType
from packages.extraction.repository import ClaimRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    return ClaimRepository(mock_session)


class TestClaimRepository:
    @pytest.mark.asyncio
    async def test_create_claim(self, repository, mock_session):
        paper_id = uuid4()
        claim = await repository.create_claim(
            paper_id=paper_id,
            claim_type="dataset",
            claim_text="Test dataset",
            normalized_value={"name": "TestDataset"},
            confidence=0.9,
            status=ClaimStatus.EXTRACTED,
        )

        assert isinstance(claim, Claim)
        assert claim.paper_id == paper_id
        assert claim.claim_type == "dataset"
        assert claim.confidence == 0.9
        assert claim.status == ClaimStatus.EXTRACTED
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session):
        claim_id = uuid4()
        mock_claim = MagicMock(spec=Claim)
        mock_claim.id = claim_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_claim
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(claim_id)

        assert result == mock_claim

    @pytest.mark.asyncio
    async def test_get_by_paper(self, repository, mock_session):
        paper_id = uuid4()
        mock_claims = [MagicMock(spec=Claim) for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_claims
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_paper(paper_id)

        assert result == mock_claims

    @pytest.mark.asyncio
    async def test_get_by_paper_and_type(self, repository, mock_session):
        paper_id = uuid4()
        mock_claim = MagicMock(spec=Claim)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_claim
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_paper_and_type(paper_id, "dataset")

        assert result == mock_claim

    @pytest.mark.asyncio
    async def test_update_claim(self, repository, mock_session):
        claim_id = uuid4()
        mock_claim = MagicMock(spec=Claim)
        mock_claim.id = claim_id
        mock_claim.claim_type = "dataset"
        mock_claim.status = ClaimStatus.EXTRACTED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_claim
        mock_session.execute.return_value = mock_result

        result = await repository.update_claim(claim_id, status=ClaimStatus.VERIFIED, confidence=0.95)

        assert result == mock_claim
        assert mock_claim.status == ClaimStatus.VERIFIED
        assert mock_claim.confidence == 0.95
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_evidence_link(self, repository, mock_session):
        claim_id = uuid4()
        chunk_id = uuid4()

        evidence_link = await repository.add_evidence_link(
            claim_id=claim_id,
            chunk_id=chunk_id,
            page_number=5,
            support_type=SupportType.SUPPORTS,
            match_score=0.9,
        )

        assert isinstance(evidence_link, EvidenceLink)
        assert evidence_link.claim_id == claim_id
        assert evidence_link.chunk_id == chunk_id
        assert evidence_link.page_number == 5
        assert evidence_link.match_score == 0.9
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_claim(self, repository, mock_session):
        claim_id = uuid4()
        mock_claim = MagicMock(spec=Claim)
        mock_claim.id = claim_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_claim
        mock_session.execute.return_value = mock_result

        result = await repository.delete_claim(claim_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_claim)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_paper(self, repository, mock_session):
        paper_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        count = await repository.count_by_paper(paper_id)

        assert count == 5
        mock_session.execute.assert_called_once()
