from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from packages.retrieval.schemas import EvidenceHit, SearchResponse, SearchType
from packages.verification.report_generator import ReportGenerationService
from packages.verification.schemas import (
    ReportRequest,
    VerificationRequest,
    VerificationStatus,
)
from packages.verification.verifier import CitationVerificationService


@pytest.fixture
def mock_retrieval_service():
    svc = MagicMock()
    svc.search = AsyncMock()
    svc.search.return_value = SearchResponse(
        hits=[
            EvidenceHit(
                evidence_id="chunk-1",
                text="The model achieved 98.2% accuracy on CIC-IDS2017 dataset with low false positive rate.",
                score=0.92,
                paper_id=uuid.uuid4(),
                paper_title="Paper 1",
                page_number=1,
                search_type=SearchType.HYBRID,
                metadata={"title": "Paper 1"},
            )
        ],
        query="The model achieves 98.2% accuracy",
        total=1,
        search_type=SearchType.HYBRID,
        took_ms=10,
    )
    return svc


@pytest.fixture
def mock_extraction_service():
    svc = MagicMock()
    svc.get_paper_claims = AsyncMock()
    svc.get_paper_claims.return_value = []
    return svc


def test_split_into_atomic_claims(mock_extraction_service, mock_retrieval_service):
    svc = CitationVerificationService(mock_extraction_service, mock_retrieval_service, "mock")
    text = "The model achieves 98.2% accuracy on CIC-IDS2017. Furthermore, it reduces false alarms significantly! Cross-dataset performance remains challenging."
    claims = svc.split_into_atomic_claims(text)
    assert len(claims) == 3
    assert "98.2% accuracy" in claims[0]


def test_classify_claim_type(mock_extraction_service, mock_retrieval_service):
    svc = CitationVerificationService(mock_extraction_service, mock_retrieval_service, "mock")
    assert (
        svc.classify_claim_type("In our opinion, this model is the most promising candidate.")
        == "opinion"
    )
    assert (
        svc.classify_claim_type("The dataset consists of 40M network flows captured over 30 days.")
        == "factual"
    )
    assert (
        svc.classify_claim_type(
            "A major limitation is the high computational complexity during inference."
        )
        == "factual"
    )


@pytest.mark.asyncio
async def test_verify_draft(mock_extraction_service, mock_retrieval_service):
    svc = CitationVerificationService(mock_extraction_service, mock_retrieval_service, "mock")
    paper_id = uuid.uuid4()
    req = VerificationRequest(
        draft_text="The model achieved 98.2% accuracy on CIC-IDS2017. It suffers from inference latency.",
        paper_ids=[paper_id],
        strict_mode=False,
    )
    result = await svc.verify_draft(req)
    assert result.total_claims >= 2
    assert result.overall_status in (
        VerificationStatus.SUPPORTED,
        VerificationStatus.PARTIALLY_SUPPORTED,
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.OPINION,
    )
    assert len(result.atomic_claims) >= 2


@pytest.mark.asyncio
async def test_generate_report(mock_extraction_service, mock_retrieval_service):
    verifier = CitationVerificationService(mock_extraction_service, mock_retrieval_service, "mock")

    synth_mock = MagicMock()
    synth_mock.run_synthesis = AsyncMock()
    from packages.synthesis.schemas import SynthesisResponse

    synth_mock.run_synthesis.return_value = SynthesisResponse(
        synthesis_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        comparison_tables=[],
        conflicts=[],
        gaps=[],
    )

    report_svc = ReportGenerationService(
        extraction_service=mock_extraction_service,
        synthesis_service=synth_mock,
        verification_service=verifier,
    )

    p1 = uuid.uuid4()
    req = ReportRequest(
        project_id=uuid.uuid4(),
        paper_ids=[p1],
        include_comparison_tables=True,
        include_gaps=True,
    )

    resp = await report_svc.generate_report(req)
    assert f"{p1}" in resp.title
    assert resp.project_id == req.project_id
    assert len(resp.sections) > 0
