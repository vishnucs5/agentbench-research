from __future__ import annotations

from packages.extraction.schemas import (
    CLAIM_SCHEMAS,
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    ClaimStatus,
    ClaimType,
    DatasetClaim,
    EvidenceLinkRequest,
    EvidenceLinkResponse,
    ExtractionJobStatus,
    FutureWorkClaim,
    LimitationClaim,
    ModelClaim,
    ResearchProblemClaim,
    ResultsClaim,
    SupportType,
)


class TestClaimTypes:
    def test_claim_type_enum(self):
        assert ClaimType.RESEARCH_PROBLEM.value == "research_problem"
        assert ClaimType.DATASET.value == "dataset"
        assert ClaimType.PREPROCESSING.value == "preprocessing"
        assert ClaimType.MODEL.value == "model"
        assert ClaimType.METRICS.value == "metrics"
        assert ClaimType.RESULTS.value == "results"
        assert ClaimType.LIMITATIONS.value == "limitations"
        assert ClaimType.FUTURE_WORK.value == "future_work"

    def test_claim_status_enum(self):
        assert ClaimStatus.EXTRACTED.value == "extracted"
        assert ClaimStatus.VERIFIED.value == "verified"
        assert ClaimStatus.NOT_REPORTED.value == "not_reported"

    def test_support_type_enum(self):
        assert SupportType.SUPPORTS.value == "supports"
        assert SupportType.PARTIALLY_SUPPORTS.value == "partially_supports"
        assert SupportType.CONTRADICTS.value == "contradicts"
        assert SupportType.UNRELATED.value == "unrelated"

    def test_claim_schemas_mapping(self):
        assert CLAIM_SCHEMAS[ClaimType.RESEARCH_PROBLEM] == ResearchProblemClaim
        assert CLAIM_SCHEMAS[ClaimType.DATASET] == DatasetClaim
        assert CLAIM_SCHEMAS[ClaimType.MODEL] == ModelClaim
        assert CLAIM_SCHEMAS[ClaimType.RESULTS] == ResultsClaim
        assert CLAIM_SCHEMAS[ClaimType.LIMITATIONS] == LimitationClaim
        assert CLAIM_SCHEMAS[ClaimType.FUTURE_WORK] == FutureWorkClaim


class TestResearchProblemClaim:
    def test_creation(self):
        claim = ResearchProblemClaim(
            problem_statement="Test problem",
            motivation="Test motivation",
            hypotheses=["H1", "H2"],
            research_questions=["RQ1"],
            objectives=["Obj1"],
        )
        assert claim.problem_statement == "Test problem"
        assert len(claim.hypotheses) == 2

    def test_defaults(self):
        claim = ResearchProblemClaim()
        assert claim.problem_statement is None
        assert claim.hypotheses == []


class TestDatasetClaim:
    def test_creation(self):
        claim = DatasetClaim(
            name="TestDataset",
            description="A test dataset",
            size="1000 samples",
            splits={"train": 800, "test": 200},
            source="https://example.com",
        )
        assert claim.name == "TestDataset"
        assert claim.splits["train"] == 800

    def test_defaults(self):
        claim = DatasetClaim()
        assert claim.name is None
        assert claim.splits == {}


class TestModelClaim:
    def test_creation(self):
        claim = ModelClaim(
            name="BERT",
            architecture="Transformer",
            framework="PyTorch",
            parameters="110M",
            hyperparameters={"lr": 2e-5},
        )
        assert claim.name == "BERT"
        assert claim.hyperparameters["lr"] == 2e-5


class TestResultsClaim:
    def test_creation(self):
        claim = ResultsClaim(
            metric_results={"accuracy": {"value": 0.95}, "f1": {"value": 0.93}},
            best_results={"accuracy": {"value": 0.95}},
            comparison_results={"baseline": {"value": 0.85}},
            qualitative_findings=["Finding 1"],
        )
        assert claim.metric_results["accuracy"]["value"] == 0.95
        assert len(claim.qualitative_findings) == 1


class TestLimitationClaim:
    def test_creation(self):
        claim = LimitationClaim(
            limitation_text="Small dataset",
            severity="medium",
            category="data",
            impact="May not generalize",
        )
        assert claim.limitation_text == "Small dataset"
        assert claim.severity == "medium"


class TestFutureWorkClaim:
    def test_creation(self):
        claim = FutureWorkClaim(
            suggestion="Try larger dataset",
            priority="high",
            category="data",
        )
        assert claim.suggestion == "Try larger dataset"
        assert claim.priority == "high"


class TestClaimExtractionRequest:
    def test_creation(self):
        import uuid

        req = ClaimExtractionRequest(
            paper_id=uuid.uuid4(),
            claim_types=[ClaimType.DATASET, ClaimType.MODEL],
        )
        assert len(req.claim_types) == 2
        assert req.force_reextract is False

    def test_defaults(self):
        import uuid

        req = ClaimExtractionRequest(paper_id=uuid.uuid4())
        assert req.claim_types == []
        assert req.chunk_ids is None


class TestClaimExtractionResponse:
    def test_creation(self):
        import uuid

        resp = ClaimExtractionResponse(
            claim_id=uuid.uuid4(),
            claim_type=ClaimType.DATASET,
            claim_text="Dataset extracted",
            normalized_value={"name": "Test"},
            confidence=0.9,
            status=ClaimStatus.EXTRACTED,
            evidence_ids=["ev_1", "ev_2"],
        )
        assert resp.claim_type == ClaimType.DATASET
        assert resp.confidence == 0.9
        assert len(resp.evidence_ids) == 2


class TestEvidenceLink:
    def test_evidence_link_request(self):
        import uuid

        req = EvidenceLinkRequest(
            claim_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            page_number=5,
            support_type=SupportType.SUPPORTS,
            match_score=0.95,
        )
        assert req.page_number == 5
        assert req.match_score == 0.95

    def test_evidence_link_response(self):
        import uuid

        resp = EvidenceLinkResponse(
            evidence_id="ev_123",
            claim_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            page_number=10,
            support_type=SupportType.SUPPORTS,
            match_score=0.9,
        )
        assert resp.evidence_id == "ev_123"


class TestExtractionJobStatus:
    def test_creation(self):
        import uuid
        from datetime import datetime

        job = ExtractionJobStatus(
            job_id=uuid.uuid4(),
            paper_id=uuid.uuid4(),
            status="processing",
            progress=0.5,
            current_claim_type="dataset",
            claims_extracted=3,
            started_at=datetime.utcnow(),
        )
        assert job.progress == 0.5
        assert job.claims_extracted == 3
        assert job.status == "processing"
