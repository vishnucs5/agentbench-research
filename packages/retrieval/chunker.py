from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from packages.ingestion.schemas import ParsedPage, ParsedPaper
from packages.retrieval.schemas import ChunkRequest


@dataclass
class Chunk:
    chunk_id: str
    paper_id: uuid.UUID
    page_number: int
    section_label: str | None
    text: str
    token_count: int
    metadata: dict[str, Any]


class ChunkingService:
    def __init__(
        self, chunk_size: int = 512, chunk_overlap: int = 50, preserve_sections: bool = True
    ):
        if not (0 <= chunk_overlap < chunk_size):
            raise ValueError("chunk_overlap must satisfy 0 <= overlap < size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_sections = preserve_sections

    def chunk_paper(
        self, paper: ParsedPaper, paper_id: uuid.UUID, request: ChunkRequest | None = None
    ) -> list[Chunk]:
        if request:
            chunk_size = request.chunk_size
            chunk_overlap = request.chunk_overlap
            preserve_sections = request.preserve_sections
        else:
            chunk_size = self.chunk_size
            chunk_overlap = self.chunk_overlap
            preserve_sections = self.preserve_sections

        all_chunks: list[Chunk] = []

        for page in paper.pages:
            page_chunks = self._chunk_page(
                page=page,
                paper_id=paper_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_sections=preserve_sections,
            )
            all_chunks.extend(page_chunks)

        return all_chunks

    def _chunk_page(
        self,
        page: ParsedPage,
        paper_id: uuid.UUID,
        chunk_size: int,
        chunk_overlap: int,
        preserve_sections: bool,
    ) -> list[Chunk]:
        text = page.text
        if not text.strip():
            return []

        if preserve_sections and page.section_label:
            sections = self._split_by_sections(text, page.section_label)
            chunks: list[Chunk] = []
            for section_text, section_label in sections:
                section_chunks = self._create_chunks(
                    text=section_text,
                    paper_id=paper_id,
                    page_number=page.page_number,
                    section_label=section_label,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                chunks.extend(section_chunks)
            return chunks
        else:
            return self._create_chunks(
                text=text,
                paper_id=paper_id,
                page_number=page.page_number,
                section_label=page.section_label,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

    def _split_by_sections(
        self, text: str, default_section: str | None
    ) -> list[tuple[str, str | None]]:
        import re

        lines = text.split("\n")
        sections: list[tuple[str, str | None]] = []
        current_section = default_section
        current_text: list[str] = []

        for line in lines:
            header_match = re.match(r"^(\d+(\.\d+)*)\s+(.+)$", line.strip())
            if header_match and len(line.strip()) < 100:
                if current_text:
                    sections.append(("\n".join(current_text).strip(), current_section))
                current_section = header_match.group(3).strip()
                current_text = [line]
            else:
                current_text.append(line)

        if current_text:
            sections.append(("\n".join(current_text).strip(), current_section))

        return [(t, s) for t, s in sections if t.strip()]

    def _create_chunks(
        self,
        text: str,
        paper_id: uuid.UUID,
        page_number: int,
        section_label: str | None,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Chunk]:
        if not (0 <= chunk_overlap < chunk_size):
            raise ValueError("chunk_overlap must satisfy 0 <= overlap < size")
        words = text.split()
        if not words:
            return []

        chunks: list[Chunk] = []
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            token_count = self._estimate_tokens(chunk_text)

            chunk = Chunk(
                chunk_id=f"{paper_id}-p{page_number}-c{len(chunks)}",
                paper_id=paper_id,
                page_number=page_number,
                section_label=section_label,
                text=chunk_text,
                token_count=token_count,
                metadata={
                    "start_word": start,
                    "end_word": end,
                    "total_words": len(words),
                },
            )
            chunks.append(chunk)

            if end >= len(words):
                break
            start = end - chunk_overlap

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)


def create_chunker(
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    preserve_sections: bool = True,
) -> ChunkingService:
    return ChunkingService(chunk_size, chunk_overlap, preserve_sections)
