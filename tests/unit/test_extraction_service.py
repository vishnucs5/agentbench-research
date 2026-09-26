from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from packages.extraction.repository import ClaimRepository
from packages.extraction.schemas import (
    ClaimExtractionRequest,
    ClaimStatus,
    ClaimType,
    EvidenceLinkRequest,
)
from packages.extraction.service import ExtractionService
from packages.ingestion.schemas import PaperMetadata, ParsedPage, ParsedPaper
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.complete = AsyncMock()
    return provider


@pytest.fixture
def mock_repo():
    repo = AsyncMock(spec=ClaimRepository)
    repo.create_claim = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_paper = AsyncMock()
    repo.add_evidence_link = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session, mock_provider, mock_repo):
    with patch("packages.extraction.service.get_provider", return_value=mock_provider):
        return ExtractionService(mock_session, repo=mock_repo)


@pytest.fixture
def sample_parsed_paper():
    return ParsedPaper(
        metadata=PaperMetadata(title="Test Paper", authors=[{"name": "Author"}], year=2024),
        pages=[
            ParsedPage(page_number=1, text="Introduction text", char_count=17, token_count=5),
            ParsedPage(page_number=2, text="Methods text", char_count=12, token_count=4),
        ],
        parser_version="1.0.0",
        sha256="abc123",
    )


class TestExtractionService:
    @pytest.mark.asyncio
    async def test_extract_claims_success(
        self, service, mock_provider, mock_repo, sample_parsed_paper
    ):
        paper_id = uuid4()
        request = ClaimExtractionRequest(
            paper_id=paper_id,
            claim_types=[ClaimType.DATASET, ClaimType.MODEL],
        )

        mock_response = MagicMock()
        mock_response.content = '{"name": "TestDataset"}'
        mock_response.finish_reason = "stop"
        mock_response.usage = {"prompt_tokens": 100}
        mock_response.model = "test-model"
        mock_provider.complete.return_value = mock_response

        mock_claim = MagicMock()
        mock_claim.id = uuid4()
        mock_repo.create_claim = AsyncMock(return_value=mock_claim)

        results = await service.extract_claims(paper_id, sample_parsed_paper, request)

        assert len(results) == 2
        assert results[0].claim_type == ClaimType.DATASET
        assert results[1].claim_type == ClaimType.MODEL
        assert mock_provider.complete.call_count == 2
        assert mock_repo.create_claim.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_claims_uses_all_types_when_none(
        self, service, mock_provider, mock_repo, sample_parsed_paper
    ):
        paper_id = uuid4()
        request = ClaimExtractionRequest(paper_id=paper_id)

        mock_response = MagicMock()
        mock_response.content = '{"name": "Test"}'
        mock_response.finish_reason = "stop"
        mock_response.usage = {}
        mock_response.model = "test-model"
        mock_provider.complete.return_value = mock_response

        mock_claim = MagicMock()
        mock_claim.id = uuid4()
        mock_repo.create_claim = AsyncMock(return_value=mock_claim)

        results = await service.extract_claims(paper_id, sample_parsed_paper, request)

        assert len(results) == 8  # All claim types

    @pytest.mark.asyncio
    async def test_extract_claims_handles_error(
        self, service, mock_provider, mock_repo, sample_parsed_paper
    ):
        paper_id = uuid4()
        request = ClaimExtractionRequest(
            paper_id=paper_id,
            claim_types=[ClaimType.DATASET],
        )

        mock_provider.complete.side_effect = Exception("API Error")

        results = await service.extract_claims(paper_id, sample_parsed_paper, request)

        # When there's an error, the service skips the claim
        assert len(results) == 0
        mock_repo.create_claim.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_evidence(self, service, mock_repo):
        claim_id = uuid4()
        chunk_id = uuid4()
        request = EvidenceLinkRequest(
            claim_id=claim_id,
            chunk_id=chunk_id,
            page_number=5,
        )

        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence.claim_id = claim_id
        mock_evidence.chunk_id = chunk_id
        mock_evidence.page_number = 5
        mock_evidence.support_type = "supports"
        mock_evidence.match_score = 0.0
        mock_repo.add_evidence_link = AsyncMock(return_value=mock_evidence)

        result = await service.link_evidence(request)

        assert result.claim_id == claim_id
        assert result.chunk_id == chunk_id
        assert result.page_number == 5

    @pytest.mark.asyncio
    async def test_get_claim(self, service, mock_repo):
        claim_id = uuid4()
        mock_claim = MagicMock()
        mock_claim.id = claim_id
        mock_claim.claim_type = "dataset"
        mock_claim.claim_text = "Test dataset"
        mock_claim.normalized_value_json = {"name": "Test"}
        mock_claim.confidence = 0.9
        mock_claim.status = ClaimStatus.EXTRACTED
        mock_claim.evidence_links = []

        mock_repo.get_by_id = AsyncMock(return_value=mock_claim)

        result = await service.get_claim(claim_id)

        assert result.claim_id == claim_id
        assert result.claim_type.value == "dataset"

    @pytest.mark.asyncio
    async def test_get_claim_not_found(self, service, mock_repo):
        claim_id = uuid4()

        mock_repo.get_by_id = AsyncMock(return_value=None)

        result = await service.get_claim(claim_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_paper_claims(self, service, mock_repo):
        paper_id = uuid4()
        mock_claims = []
        for i in range(3):
            claim = MagicMock()
            claim.id = uuid4()
            claim.claim_type = "dataset"
            claim.claim_text = f"Claim {i}"
            claim.normalized_value_json = {}
            claim.confidence = 0.8
            claim.status = ClaimStatus.EXTRACTED
            claim.evidence_links = []
            mock_claims.append(claim)

        mock_repo.get_by_paper = AsyncMock(return_value=mock_claims)

        results = await service.get_paper_claims(paper_id)

        assert len(results) == 3

    def test_get_job_status(self, service):
        job_id = uuid4()
        paper_id = uuid4()

        from datetime import datetime

        from packages.extraction.schemas import ExtractionJobStatus

        job = ExtractionJobStatus(
            job_id=job_id,
            paper_id=paper_id,
            status="completed",
            progress=1.0,
            current_claim_type=None,
            claims_extracted=5,
            started_at=datetime.utcnow(),
        )
        service._jobs[job_id] = job

        result = service.get_job_status(job_id)
        assert result == job

        result = service.get_job_status(uuid4())
        assert result is None
