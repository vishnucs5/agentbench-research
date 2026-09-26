from __future__ import annotations

import re
from abc import ABC, abstractmethod

import fitz


class DocumentParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_data: bytes, filename: str) -> str:
        """Extract readable text from file data.

        Args:
            file_data: Raw file bytes
            filename: Original filename (used for format detection)

        Returns:
            Extracted text content
        """
        pass

    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """Return list of supported MIME types."""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass


class PDFParser(DocumentParser):
    """Parser for PDF documents using PyMuPDF."""

    def parse(self, file_data: bytes, filename: str) -> str:
        doc = fitz.open(stream=file_data, filetype="pdf")

        try:
            pages_text = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text("text")
                text = self._clean_text(text)
                if text.strip():
                    pages_text.append(text)
            return "\n\n".join(pages_text)
        finally:
            doc.close()

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\x00", "", text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def supported_mime_types(self) -> list[str]:
        return ["application/pdf"]

    def supported_extensions(self) -> list[str]:
        return [".pdf"]


class TextParser(DocumentParser):
    """Parser for plain text files."""

    def parse(self, file_data: bytes, filename: str) -> str:
        # Try multiple encodings (avoid utf-16 false positive)
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                text = file_data.decode(encoding)
                # Heuristic: if decoded text contains many replacement chars, try next
                if "\ufffd" not in text:
                    return self._clean_text(text)
            except UnicodeDecodeError:
                continue
        # Fallback: replace undecodable bytes
        return self._clean_text(file_data.decode("utf-8", errors="replace"))

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\x00", "", text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def supported_mime_types(self) -> list[str]:
        return ["text/plain"]

    def supported_extensions(self) -> list[str]:
        return [".txt"]


class DocxParser(DocumentParser):
    """Parser for DOCX files using python-docx."""

    def __init__(self) -> None:
        self._docx_available = self._check_docx()

    def _check_docx(self) -> bool:
        try:
            import docx  # noqa: F401

            return True
        except ImportError:
            return False

    def parse(self, file_data: bytes, filename: str) -> str:
        if not self._docx_available:
            raise RuntimeError(
                "python-docx is not installed. Install with: pip install python-docx"
            )

        import io

        from docx import Document

        doc = Document(io.BytesIO(file_data))
        paragraphs = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        row_text.append(cell_text)
                if row_text:
                    paragraphs.append(" | ".join(row_text))

        return "\n\n".join(paragraphs)

    def supported_mime_types(self) -> list[str]:
        return ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

    def supported_extensions(self) -> list[str]:
        return [".docx"]


class DocumentParserFactory:
    """Factory for creating appropriate document parsers."""

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = [
            PDFParser(),
            TextParser(),
            DocxParser(),
        ]

    def get_parser(self, filename: str, mime_type: str | None = None) -> DocumentParser:
        """Get appropriate parser for file based on extension and MIME type."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        ext = f".{ext}" if ext else ""

        # Try exact MIME type match first
        if mime_type:
            for parser in self._parsers:
                if mime_type in parser.supported_mime_types():
                    return parser

        # Fall back to extension match
        for parser in self._parsers:
            if ext in parser.supported_extensions():
                return parser

        # Default to text parser
        return TextParser()

    def is_supported(self, filename: str, mime_type: str | None = None) -> bool:
        """Check if file type is supported."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        ext = f".{ext}" if ext else ""

        if mime_type:
            for parser in self._parsers:
                if mime_type in parser.supported_mime_types():
                    return True

        for parser in self._parsers:
            if ext in parser.supported_extensions():
                return True

        return False

    def get_all_supported_mime_types(self) -> list[str]:
        """Get all supported MIME types."""
        types = []
        for parser in self._parsers:
            types.extend(parser.supported_mime_types())
        return list(set(types))

    def get_all_supported_extensions(self) -> list[str]:
        """Get all supported file extensions."""
        exts = []
        for parser in self._parsers:
            exts.extend(parser.supported_extensions())
        return list(set(exts))


def create_parser() -> DocumentParserFactory:
    """Create a document parser factory."""
    return DocumentParserFactory()
