from __future__ import annotations

import hashlib
import re
from typing import Any

import fitz

from .schemas import PaperMetadata, ParsedPage, ParsedPaper


class PDFParser:
    def __init__(self, parser_version: str = "1.0.0"):
        self.parser_version = parser_version

    def parse(self, pdf_data: bytes) -> ParsedPaper:
        sha256 = hashlib.sha256(pdf_data).hexdigest()
        doc = fitz.open(stream=pdf_data, filetype="pdf")

        try:
            metadata = self._extract_metadata(doc)
            pages = self._extract_pages(doc)

            return ParsedPaper(
                metadata=metadata,
                pages=pages,
                parser_version=self.parser_version,
                sha256=sha256,
            )
        finally:
            doc.close()

    def _extract_metadata(self, doc: fitz.Document) -> PaperMetadata:
        meta = doc.metadata or {}

        authors = []
        if meta.get("author"):
            for author in meta["author"].split(";"):
                author = author.strip()
                if author:
                    authors.append({"name": author})

        return PaperMetadata(
            title=meta.get("title") or None,
            authors=authors,
            year=self._parse_year(meta.get("creationDate")),
            subject=meta.get("subject") or None,
            keywords=self._parse_keywords(meta.get("keywords")),
            producer=meta.get("producer") or None,
            creator=meta.get("creator") or None,
            creation_date=self._parse_pdf_date(meta.get("creationDate")),
            modification_date=self._parse_pdf_date(meta.get("modDate")),
            page_count=doc.page_count,
        )

    def _extract_pages(self, doc: fitz.Document) -> list[ParsedPage]:
        pages = []
        for page_num in range(doc.page_count):
            page = doc[page_num]

            text = page.get_text("text")
            text = self._clean_text(text)

            section_label = self._detect_section(text, page_num)

            char_count = len(text)
            token_count = self._estimate_tokens(text)

            pages.append(
                ParsedPage(
                    page_number=page_num + 1,
                    text=text,
                    section_label=section_label,
                    char_count=char_count,
                    token_count=token_count,
                    ocr_used=False,
                )
            )

        return pages

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\x00", "", text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def _detect_section(self, text: str, page_num: int) -> str | None:
        lines = text.split("\n")
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            if re.match(r"^\d+(\.\d+)*\s+[A-Z]", line):
                return line[:100]
            if re.match(r"^[A-Z][A-Z\s]{2,}:?$", line) and len(line) < 80:
                return line
        return None

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _parse_year(self, date_str: str | None) -> int | None:
        if not date_str:
            return None
        match = re.search(r"D:(\d{4})", date_str)
        if match:
            return int(match.group(1))
        return None

    def _parse_keywords(self, keywords_str: str | None) -> list[str]:
        if not keywords_str:
            return []
        return [k.strip() for k in re.split(r"[;,]", keywords_str) if k.strip()]

    def _parse_pdf_date(self, date_str: str | None) -> Any:
        if not date_str:
            return None
        match = re.search(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", date_str)
        if match:
            from datetime import datetime

            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                int(match.group(5)),
                int(match.group(6)),
            )
        return None


def create_parser(parser_version: str = "1.0.0") -> PDFParser:
    return PDFParser(parser_version)
