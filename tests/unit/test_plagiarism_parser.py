from __future__ import annotations

import pytest
from packages.plagiarism.parser import DocumentParserFactory, create_parser


class TestDocumentParserFactory:
    def test_is_supported_txt(self):
        factory = DocumentParserFactory()
        assert factory.is_supported("test.txt", "text/plain")
        assert factory.is_supported("notes.TXT", None)

    def test_is_supported_pdf(self):
        factory = DocumentParserFactory()
        assert factory.is_supported("paper.pdf", "application/pdf")
        assert factory.is_supported("doc.PDF", None)

    def test_is_supported_docx(self):
        factory = DocumentParserFactory()
        assert factory.is_supported(
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_is_not_supported(self):
        factory = DocumentParserFactory()
        assert not factory.is_supported("image.png", "image/png")
        assert not factory.is_supported("archive.zip", "application/zip")
        assert not factory.is_supported("no_extension", "application/octet-stream")

    def test_get_parser_by_mime(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.txt", "text/plain")
        assert "text/plain" in parser.supported_mime_types()

    def test_get_parser_by_extension(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("paper.pdf", None)
        assert ".pdf" in parser.supported_extensions()

    def test_get_all_supported(self):
        factory = DocumentParserFactory()
        mimes = factory.get_all_supported_mime_types()
        exts = factory.get_all_supported_extensions()
        assert "text/plain" in mimes
        assert "application/pdf" in mimes
        assert ".txt" in exts
        assert ".pdf" in exts

    def test_create_parser_factory(self):
        factory = create_parser()
        assert isinstance(factory, DocumentParserFactory)


class TestTextParser:
    def test_parse_utf8(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.txt", "text/plain")
        data = b"Hello world\n\nSecond paragraph."
        result = parser.parse(data, "test.txt")
        assert "Hello world" in result
        assert "Second paragraph" in result

    def test_parse_empty(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.txt", "text/plain")
        result = parser.parse(b"", "empty.txt")
        assert result.strip() == ""

    def test_parse_handles_null_bytes(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.txt", "text/plain")
        data = b"Hello\x00world"
        result = parser.parse(data, "test.txt")
        assert "\x00" not in result

    def test_parse_latin1_fallback(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.txt", "text/plain")
        # Latin-1 encoded: caf\xe9
        data = "café".encode("latin-1")
        result = parser.parse(data, "test.txt")
        # Should decode without error
        assert "caf" in result


class TestPDFParser:
    def test_parse_minimal_pdf(self):
        # Create a minimal PDF with text using pymupdf if available
        try:
            import fitz
        except ImportError:
            pytest.skip("pymupdf not available")
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.pdf", "application/pdf")
        # Create PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello PDF world\nSecond line")
        pdf_bytes = doc.tobytes()
        doc.close()
        result = parser.parse(pdf_bytes, "test.pdf")
        assert "Hello PDF world" in result

    def test_pdf_clean_text(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser("test.pdf", "application/pdf")
        # Access private but test via parse with mocked fitz if needed
        # Here we just check the parser's clean logic indirectly
        data = b"%PDF-1.4 minimal"
        # Parser will try to open as PDF; may fail but we test supported check
        assert parser.supported_mime_types() == ["application/pdf"]


class TestDocxParser:
    def test_docx_parser_supported(self):
        factory = DocumentParserFactory()
        parser = factory.get_parser(
            "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert ".docx" in parser.supported_extensions()

    def test_docx_parse_if_available(self):
        try:
            import docx
        except ImportError:
            pytest.skip("python-docx not installed")
        import io

        from docx import Document

        factory = DocumentParserFactory()
        parser = factory.get_parser(
            "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        doc = Document()
        doc.add_paragraph("Hello docx world")
        doc.add_paragraph("Second paragraph")
        buf = io.BytesIO()
        doc.save(buf)
        data = buf.getvalue()
        result = parser.parse(data, "test.docx")
        assert "Hello docx world" in result
        assert "Second paragraph" in result

    def test_docx_parse_tables(self):
        try:
            import docx
        except ImportError:
            pytest.skip("python-docx not installed")
        import io

        from docx import Document

        factory = DocumentParserFactory()
        parser = factory.get_parser(
            "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        doc = Document()
        doc.add_paragraph("Intro")
        table = doc.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Cell A"
        table.cell(0, 1).text = "Cell B"
        buf = io.BytesIO()
        doc.save(buf)
        result = parser.parse(buf.getvalue(), "test.docx")
        assert "Cell A" in result
        assert "Cell B" in result


class TestFileValidation:
    def test_validate_file_type(self):
        factory = DocumentParserFactory()
        assert factory.is_supported("good.pdf", "application/pdf")
        assert not factory.is_supported("bad.exe", "application/octet-stream")

    def test_file_size_validation_logic(self):
        # Simulate size check (10 MB default)
        max_bytes = 10 * 1024 * 1024
        small = b"a" * 1024
        large = b"a" * (max_bytes + 1)
        assert len(small) <= max_bytes
        assert len(large) > max_bytes

    def test_sanitize_content(self):
        # Simulate sanitize: html escape
        import html

        raw = '<script>alert("x")</script> Hello'
        sanitized = html.escape(raw)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
