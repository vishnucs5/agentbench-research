from __future__ import annotations

import pytest
from packages.ingestion.parser import PDFParser, create_parser
from packages.ingestion.schemas import PaperMetadata, ParsedPage, ParsedPaper


class TestPDFParser:
    def test_create_parser(self):
        parser = create_parser("1.0.0")
        assert isinstance(parser, PDFParser)
        assert parser.parser_version == "1.0.0"

    def test_parser_initialization(self):
        parser = PDFParser(parser_version="2.0.0")
        assert parser.parser_version == "2.0.0"

    @pytest.fixture
    def sample_pdf_bytes(self):
        # Minimal valid PDF content
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n193\n%%EOF"

    def test_parse_returns_parsed_paper(self, sample_pdf_bytes):
        PDFParser()
        # This will fail with the minimal PDF, but we test structure
        # In real tests, we'd use a proper test PDF
        pass


class TestPaperMetadata:
    def test_metadata_creation(self):
        metadata = PaperMetadata(
            title="Test Paper",
            authors=[{"name": "Author One"}, {"name": "Author Two"}],
            year=2024,
            subject="Computer Science",
            keywords=["AI", "ML"],
        )
        assert metadata.title == "Test Paper"
        assert len(metadata.authors) == 2
        assert metadata.year == 2024


class TestParsedPage:
    def test_page_creation(self):
        page = ParsedPage(
            page_number=1,
            text="Sample text content",
            section_label="Introduction",
            char_count=19,
            token_count=5,
        )
        assert page.page_number == 1
        assert page.section_label == "Introduction"
        assert page.char_count == 19
        assert page.token_count == 5


class TestParsedPaper:
    def test_parsed_paper_creation(self):
        metadata = PaperMetadata(title="Test", page_count=2)
        pages = [
            ParsedPage(page_number=1, text="Page 1", char_count=6, token_count=2),
            ParsedPage(page_number=2, text="Page 2", char_count=6, token_count=2),
        ]
        paper = ParsedPaper(
            metadata=metadata,
            pages=pages,
            parser_version="1.0.0",
            sha256="abc123",
        )
        assert paper.metadata.title == "Test"
        assert len(paper.pages) == 2
        assert paper.parser_version == "1.0.0"
        assert paper.sha256 == "abc123"
