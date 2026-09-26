from __future__ import annotations

import uuid

import pytest
from packages.retrieval.chunker import Chunk, ChunkingService
from packages.retrieval.schemas import ChunkRequest


class TestChunkingService:
    @pytest.fixture
    def chunker(self):
        return ChunkingService(chunk_size=100, chunk_overlap=20, preserve_sections=True)

    def test_chunker_creation(self):
        chunker = ChunkingService(chunk_size=512, chunk_overlap=50)
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
        assert chunker.preserve_sections is True

    def test_create_chunker_factory(self):
        chunker = ChunkingService(chunk_size=256, chunk_overlap=30, preserve_sections=False)
        assert chunker.chunk_size == 256
        assert chunker.chunk_overlap == 30
        assert chunker.preserve_sections is False

    def test_chunk_simple_text(self, chunker):
        text = "This is a simple test text that should be chunked properly."
        chunks = chunker._create_chunks(
            text=text,
            paper_id="test-paper",
            page_number=1,
            section_label="Introduction",
            chunk_size=50,
            chunk_overlap=10,
        )
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.paper_id == "test-paper"
            assert chunk.page_number == 1
            assert chunk.section_label == "Introduction"
            assert chunk.token_count > 0

    def test_chunk_empty_text(self, chunker):
        chunks = chunker._create_chunks(
            text="",
            paper_id="test-paper",
            page_number=1,
            section_label=None,
            chunk_size=100,
            chunk_overlap=20,
        )
        assert chunks == []

    def test_chunk_preserves_sections(self, chunker):
        text = "1. Introduction\nThis is the introduction section.\n\n2. Methods\nThis is the methods section."
        chunks = chunker._create_chunks(
            text=text,
            paper_id="test-paper",
            page_number=1,
            section_label="Main",
            chunk_size=50,
            chunk_overlap=10,
        )
        assert len(chunks) > 0
        sections = {c.section_label for c in chunks}
        assert len(sections) > 0

    def test_estimate_tokens(self, chunker):
        assert chunker._estimate_tokens("hello world") == 2
        assert chunker._estimate_tokens("") == 1
        assert chunker._estimate_tokens("a" * 100) == 25


class TestChunkRequest:
    def test_chunk_request_defaults(self):
        req = ChunkRequest(paper_id=uuid.uuid4())
        assert req.chunk_size == 512
        assert req.chunk_overlap == 50
        assert req.preserve_sections is True

    def test_chunk_request_custom(self):
        req = ChunkRequest(
            paper_id=uuid.uuid4(), chunk_size=256, chunk_overlap=30, preserve_sections=False
        )
        assert req.chunk_size == 256
        assert req.chunk_overlap == 30
        assert req.preserve_sections is False

    def test_chunk_request_validation(self):
        with pytest.raises(ValueError):
            ChunkRequest(paper_id="test-id", chunk_size=50)

        with pytest.raises(ValueError):
            ChunkRequest(paper_id="test-id", chunk_overlap=600)
