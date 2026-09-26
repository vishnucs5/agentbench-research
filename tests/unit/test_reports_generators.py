import uuid
from datetime import datetime, UTC
import pytest

from packages.domain.models import Paper, Project, ResearchRun, RunStatus
from packages.reports.generators.bibtex import generate_bibtex
from packages.reports.generators.latex import generate_latex_manuscript
from packages.reports.generators.markdown import generate_markdown_survey
from packages.reports.generators.audit import generate_claim_audit_log
from packages.reports.generators.plagiarism_cert import generate_plagiarism_certificate


@pytest.fixture
def sample_papers():
    p1 = Paper(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Deep Learning for Network Intrusion Detection: A Survey",
        authors_json=["A. Rahman", "L. Chen"],
        year=2024,
        doi="10.1109/SURV.2024.123456",
        source_url="IEEE Communications Surveys & Tutorials",
    )
    p2 = Paper(
        id=uuid.uuid4(),
        project_id=p1.project_id,
        title="Transformer Anomaly Detection on CICIDS2017",
        authors_json=["M. Garcia"],
        year=2023,
        doi="10.1145/3345.6789",
        source_url="ACM CCS",
    )
    return [p1, p2]


@pytest.fixture
def sample_project():
    return Project(
        id=uuid.uuid4(),
        name="Network Intrusion Detection Research",
        domain="cybersecurity",
        retention_days=30,
        owner_id=uuid.uuid4(),
    )


@pytest.fixture
def sample_runs(sample_project):
    run = ResearchRun(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        user_id=sample_project.owner_id,
        request_text="Compare deep learning architectures for anomaly detection",
        status=RunStatus.COMPLETED,
        model_profile="openrouter",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    return [run]


def test_generate_bibtex(sample_papers):
    bib_str = generate_bibtex(sample_papers)
    assert "@article{" in bib_str or "@inproceedings{" in bib_str
    assert "Deep Learning for Network Intrusion Detection" in bib_str
    assert "Rahman" in bib_str
    assert "2024" in bib_str
    assert "10.1109/SURV.2024.123456" in bib_str
    assert "Transformer Anomaly Detection" in bib_str


def test_generate_latex_manuscript(sample_project, sample_papers, sample_runs):
    latex_str = generate_latex_manuscript(
        project=sample_project,
        papers=sample_papers,
        runs=sample_runs,
    )
    assert "\\documentclass" in latex_str
    assert sample_project.name in latex_str
    assert "\\begin{document}" in latex_str
    assert "\\section{Introduction}" in latex_str
    assert "\\section{Comparative Synthesis}" in latex_str
    assert "\\begin{table*}" in latex_str
    assert "\\end{document}" in latex_str
    assert "\\cite{" in latex_str


def test_generate_markdown_survey(sample_project, sample_papers, sample_runs):
    md_str = generate_markdown_survey(
        project=sample_project,
        papers=sample_papers,
        runs=sample_runs,
    )
    assert f"# Research Survey: {sample_project.name}" in md_str
    assert "Executive Summary" in md_str
    assert "Ingested Papers Catalog" in md_str
    assert "Deep Learning for Network Intrusion Detection" in md_str
    assert "Comparative Synthesis Matrix" in md_str
    assert "| Paper | Authors | Year |" in md_str


def test_generate_claim_audit_log():
    claims = [
        {"claim_text": "Transformer achieves 97.6% accuracy.", "claim_type": "empirical_result", "page": 1},
        {"claim_text": "CNN trained with 0.001 learning rate.", "claim_type": "hyperparameter", "page": 2},
    ]
    verifications = [
        {"claim_id": "c1", "status": "supported", "confidence": 0.95, "evidence_id": "e1", "page": 1},
        {"claim_id": "c2", "status": "supported", "confidence": 0.92, "evidence_id": "e2", "page": 2},
    ]
    audit_str = generate_claim_audit_log("Cybersecurity Project", claims, verifications)
    assert "# Claim Verification Audit Log" in audit_str
    assert "Cybersecurity Project" in audit_str
    assert "Transformer achieves 97.6% accuracy." in audit_str
    assert "Supported" in audit_str or "supported" in audit_str
    assert "95" in audit_str


def test_generate_plagiarism_certificate():
    mock_check = {
        "id": "chk-12345",
        "source_filename": "draft_survey.pdf",
        "originality_score": 88.5,
        "similarity_score": 11.5,
        "verdict": "clean",
        "created_at": datetime.now(UTC),
        "total_words": 1200,
        "total_characters": 7500,
        "matches": [
            {
                "matched_passage": "Network intrusion detection systems are critical.",
                "similarity_score": 0.85,
                "source_title": "Deep Learning Survey",
                "source_page": 1,
            }
        ],
    }
    cert_html = generate_plagiarism_certificate(mock_check, format="html")
    assert "Certificate of Originality & Similarity Analysis" in cert_html
    assert "88.5%" in cert_html
    assert "draft_survey.pdf" in cert_html
    assert "Deep Learning Survey" in cert_html

    cert_md = generate_plagiarism_certificate(mock_check, format="markdown")
    assert "# Originality & Plagiarism Audit Certificate" in cert_md
    assert "88.5%" in cert_md
    assert "draft_survey.pdf" in cert_md
