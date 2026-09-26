from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from packages.extraction.schemas import ClaimType
from packages.synthesis.comparison import ComparisonService
from packages.synthesis.gap_analysis import GapAnalysisService
from packages.synthesis.normalization import NormalizationService
from packages.synthesis.schemas import (
    ComparisonType,
    SynthesisRequest,
)
from packages.synthesis.service import SynthesisService


@pytest.fixture
def sample_paper_ids():
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def sample_claims(sample_paper_ids):
    p1, p2 = sample_paper_ids
    return {
        p1: {
            ClaimType.MODEL: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "We evaluate a 1D-CNN",
                    "normalized_value": {
                        "name": "1D-CNN",
                        "architecture": "3 conv layers",
                        "framework": "TensorFlow",
                        "parameters": "1.2M",
                        "pretrained": False,
                    },
                    "confidence": 0.95,
                    "evidence_ids": ["ev-1"],
                    "paper_title": "Paper 1",
                }
            ],
            ClaimType.DATASET: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Trained on CIC-IDS2017",
                    "normalized_value": {
                        "name": "cicids2017",
                        "size": "2.8M flows",
                        "source": "CIC",
                        "splits": {"train": "80%", "test": "20%"},
                        "domain": "network intrusion",
                    },
                    "confidence": 0.9,
                    "evidence_ids": ["ev-2"],
                    "paper_title": "Paper 1",
                }
            ],
            ClaimType.RESULTS: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Achieved 98.2% accuracy on CIC-IDS2017",
                    "normalized_value": {
                        "metric_results": {"CIC-IDS2017": {"accuracy": 0.982}},
                    },
                    "confidence": 0.99,
                    "evidence_ids": ["ev-3"],
                    "paper_title": "Paper 1",
                }
            ],
            ClaimType.LIMITATIONS: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Generalization accuracy drops on cross-dataset",
                    "normalized_value": {
                        "category": "generalization",
                        "limitation_text": "Accuracy drops on cross-dataset evaluation",
                    },
                    "confidence": 0.85,
                    "evidence_ids": ["ev-4"],
                    "paper_title": "Paper 1",
                }
            ],
            ClaimType.PREPROCESSING: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Normalized using z-score",
                    "normalized_value": {
                        "steps": ["z-score normalization"],
                        "tools": ["CICFlowMeter"],
                    },
                    "confidence": 0.9,
                    "evidence_ids": ["ev-5"],
                    "paper_title": "Paper 1",
                }
            ],
        },
        p2: {
            ClaimType.MODEL: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "We propose FlowTransformer",
                    "normalized_value": {
                        "name": "FlowTransformer",
                        "architecture": "6-layer transformer",
                        "framework": "PyTorch",
                        "parameters": "22M",
                        "pretrained": True,
                    },
                    "confidence": 0.92,
                    "evidence_ids": ["ev-6"],
                    "paper_title": "Paper 2",
                }
            ],
            ClaimType.DATASET: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Evaluated on Enterprise-40M",
                    "normalized_value": {
                        "name": "enterprise-40m",
                        "size": "40M flows",
                        "source": "Private capture",
                        "splits": {"train": "70%", "test": "30%"},
                        "domain": "network intrusion",
                    },
                    "confidence": 0.9,
                    "evidence_ids": ["ev-7"],
                    "paper_title": "Paper 2",
                }
            ],
            ClaimType.RESULTS: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Achieved 97.6% accuracy on CIC-IDS2017",
                    "normalized_value": {
                        "metric_results": {"CIC-IDS2017": {"accuracy": 0.976}},
                    },
                    "confidence": 0.98,
                    "evidence_ids": ["ev-8"],
                    "paper_title": "Paper 2",
                }
            ],
            ClaimType.LIMITATIONS: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Inference efficiency is limited",
                    "normalized_value": {
                        "category": "efficiency",
                        "limitation_text": "Inference latency is high for edge devices",
                    },
                    "confidence": 0.88,
                    "evidence_ids": ["ev-9"],
                    "paper_title": "Paper 2",
                }
            ],
            ClaimType.PREPROCESSING: [
                {
                    "claim_id": uuid.uuid4(),
                    "claim_text": "Masking and flow tokenization",
                    "normalized_value": {
                        "steps": ["masking", "tokenization"],
                        "tools": ["custom exporter"],
                    },
                    "confidence": 0.85,
                    "evidence_ids": ["ev-10"],
                    "paper_title": "Paper 2",
                }
            ],
        },
    }


def test_normalization_service():
    norm = NormalizationService()
    assert norm.normalize_model("google/bert-base-uncased").normalized_value == "bert"
    assert norm.normalize_dataset("CIC-IDS2017").normalized_value == "cicids2017"
    assert norm.normalize_metric("Classification Accuracy").normalized_value == "accuracy"
    assert norm.normalize_metric("F1-Score").normalized_value == "f1"


def test_comparison_service_model_table(sample_paper_ids, sample_claims):
    comp = ComparisonService()
    project_id = uuid.uuid4()
    table = comp.build_comparison_table(
        project_id=project_id,
        paper_ids=sample_paper_ids,
        paper_claims=sample_claims,
        comparison_type=ComparisonType.MODEL,
    )
    assert table.comparison_type == ComparisonType.MODEL
    assert len(table.rows) >= 5
    attr_names = [r.attribute for r in table.rows]
    assert "Model Name" in attr_names
    assert "Architecture" in attr_names
    assert "Framework" in attr_names


def test_comparison_service_dataset_table(sample_paper_ids, sample_claims):
    comp = ComparisonService()
    project_id = uuid.uuid4()
    table = comp.build_comparison_table(
        project_id=project_id,
        paper_ids=sample_paper_ids,
        paper_claims=sample_claims,
        comparison_type=ComparisonType.DATASET,
    )
    assert table.comparison_type == ComparisonType.DATASET
    assert len(table.rows) >= 4


def test_comparison_service_results_table(sample_paper_ids, sample_claims):
    comp = ComparisonService()
    project_id = uuid.uuid4()
    table = comp.build_comparison_table(
        project_id=project_id,
        paper_ids=sample_paper_ids,
        paper_claims=sample_claims,
        comparison_type=ComparisonType.RESULTS,
    )
    assert table.comparison_type == ComparisonType.RESULTS
    assert len(table.rows) >= 1
    assert any("accuracy" in r.attribute.lower() for r in table.rows)


def test_comparison_service_limitations_table(sample_paper_ids, sample_claims):
    comp = ComparisonService()
    project_id = uuid.uuid4()
    table = comp.build_comparison_table(
        project_id=project_id,
        paper_ids=sample_paper_ids,
        paper_claims=sample_claims,
        comparison_type=ComparisonType.LIMITATIONS,
    )
    assert table.comparison_type == ComparisonType.LIMITATIONS
    assert len(table.rows) >= 1


def test_comparison_service_detect_conflicts(sample_claims):
    comp = ComparisonService()
    conflicts = comp.detect_conflicts(sample_claims)
    assert isinstance(conflicts, list)


def test_gap_analysis_service(sample_claims):
    gap_svc = GapAnalysisService()
    gaps = gap_svc.analyze_gaps(sample_claims)
    assert isinstance(gaps, list)
    assert len(gaps) > 0


@pytest.mark.asyncio
async def test_synthesis_service_run(sample_paper_ids, sample_claims):
    extraction_mock = AsyncMock()

    class FakeClaim:
        def __init__(self, data):
            self.claim_id = data.get("claim_id", uuid.uuid4())
            self.claim_type = data.get("claim_type", "model")
            self.claim_text = data.get("claim_text", "")
            self.normalized_value = data.get("normalized_value", {})
            self.confidence = data.get("confidence", 0.9)
            self.status = "extracted"
            self.evidence_ids = data.get("evidence_ids", [])
            self.paper_title = data.get("paper_title", "Paper")

    async def get_paper_claims(pid):
        claims_dict = sample_claims.get(pid, {})
        result = []
        for ctype, clist in claims_dict.items():
            for item in clist:
                item_copy = dict(item)
                item_copy["claim_type"] = ctype.value
                result.append(FakeClaim(item_copy))
        return result

    extraction_mock.get_paper_claims.side_effect = get_paper_claims

    svc = SynthesisService(extraction_service=extraction_mock)
    req = SynthesisRequest(
        project_id=uuid.uuid4(),
        paper_ids=sample_paper_ids,
        include_conflicts=True,
        include_gaps=True,
    )
    resp = await svc.run_synthesis(req)

    assert resp.project_id == req.project_id
    assert len(resp.comparison_tables) >= 5
    assert isinstance(resp.conflicts, list)
    assert isinstance(resp.gaps, list)
