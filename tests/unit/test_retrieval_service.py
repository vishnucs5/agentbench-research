from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from packages.ingestion.schemas import PaperMetadata, ParsedPage, ParsedPaper
from packages.retrieval.schemas import SearchRequest, SearchType
from packages.retrieval.service import RetrievalService


@pytest.fixture
def mock_chunker():
    chunker = MagicMock()
    chunker.chunk_paper.return_value = [
        MagicMock(
            chunk_id="chunk1",
            paper_id="paper1",
            page_number=1,
            section_label="Introduction",
            text="This is the introduction text.",
            token_count=10,
            metadata={},
        ),
        MagicMock(
            chunk_id="chunk2",
            paper_id="paper1",
            page_number=2,
            section_label="Methods",
            text="This is the methods text.",
            token_count=10,
            metadata={},
        ),
    ]
    return chunker


@pytest.fixture
def mock_embedder():
    embedder = MagicMock()
    embedder.embed_batch.return_value = [[0.1] * 384, [0.2] * 384]
    embedder.embed_single.return_value = [0.15] * 384
    return embedder


@pytest.fixture
def mock_qdrant():
    qdrant = MagicMock()
    qdrant.search_semantic.return_value = []
    qdrant.search_bm25.return_value = []
    qdrant.hybrid_search.return_value = []
    qdrant.upsert_chunks.return_value = None
    qdrant.delete_paper_chunks.return_value = None
    qdrant.get_collection_info.return_value = {"points_count": 2}
    return qdrant


@pytest.fixture
def service(mock_chunker, mock_embedder, mock_qdrant):
    return RetrievalService(chunker=mock_chunker, embedder=mock_embedder, qdrant=mock_qdrant)


@pytest.fixture
def sample_parsed_paper():
    return ParsedPaper(
        metadata=PaperMetadata(title="Test Paper", authors=[{"name": "Author"}], year=2024),
        pages=[
            ParsedPage(page_number=1, text="Introduction text", char_count=17, token_count=5),
            ParsedPage(page_number=2, text="Methods text", char_count=12, token_count=4),
        ],
        parser_version="1.0.0",
        sha256="abc123",
    )


class TestRetrievalService:
    @pytest.mark.asyncio
    async def test_index_paper(self, service, mock_chunker, mock_embedder, mock_qdrant, sample_parsed_paper):
        result = await service.index_paper(sample_parsed_paper, "paper1", "project1", {"year": 2024})

        assert result["chunk_count"] == 2
        assert result["embedded_count"] == 2
        assert result["bm25_indexed"] is True
        mock_chunker.chunk_paper.assert_called_once()
        mock_embedder.embed_batch.assert_called_once()
        mock_qdrant.upsert_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_hybrid(self, service, mock_qdrant):
        request = SearchRequest(query="test query", top_k=5, search_type=SearchType.HYBRID)
        mock_qdrant.hybrid_search.return_value = []

        result = await service.search(request)

        assert isinstance(result, type(result))
        assert result.query == "test query"
        assert result.search_type == SearchType.HYBRID
        assert result.total == 0
        mock_qdrant.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_semantic(self, service, mock_qdrant):
        request = SearchRequest(query="test query", top_k=5, search_type=SearchType.SEMANTIC)
        mock_qdrant.search_semantic.return_value = []

        result = await service.search(request)

        assert result.search_type == SearchType.SEMANTIC
        mock_qdrant.search_semantic.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_bm25(self, service, mock_qdrant):
        request = SearchRequest(query="test query", top_k=5, search_type=SearchType.BM25)
        mock_qdrant.search_bm25.return_value = []

        result = await service.search(request)

        assert result.search_type == SearchType.BM25
        mock_qdrant.search_bm25.assert_called_once()

    import uuid

    @pytest.mark.asyncio
    async def test_search_with_filters(self, service, mock_qdrant):
        request = SearchRequest(
            query="test query",
            project_id=uuid.uuid4(),
            year_from=2020,
            year_to=2024,
            author="Smith",
        )
        mock_qdrant.hybrid_search.return_value = []

        await service.search(request)

        # Check that filters were passed
        call_args = mock_qdrant.hybrid_search.call_args
        assert call_args is not None
        # filters is the 4th positional argument (query, embedding, top_k, filters)
        # args order: query_text, query_embedding, top_k, bm25_weight, semantic_weight, filters
        filters = call_args.args[5] if len(call_args.args) > 5 else call_args.kwargs.get("filters", {})
        assert "project_id" in filters
        assert filters.get("year_from") == 2020
        assert filters.get("year_to") == 2024
        assert filters.get("author") == "Smith"

    def test_delete_paper(self, service, mock_qdrant):
        service.delete_paper("paper1")
        mock_qdrant.delete_paper_chunks.assert_called_once_with("paper1")


class TestSearchRequest:
    def test_search_request_defaults(self):
        req = SearchRequest(query="test")
        assert req.query == "test"
        assert req.search_type == SearchType.HYBRID
        assert req.top_k == 10
        assert req.bm25_weight == 0.5
        assert req.semantic_weight == 0.5

    def test_search_request_custom(self):
        req = SearchRequest(
            query="test",
            search_type=SearchType.SEMANTIC,
            top_k=20,
            bm25_weight=0.3,
            semantic_weight=0.7,
        )
        assert req.search_type == SearchType.SEMANTIC
        assert req.top_k == 20
        assert req.bm25_weight == 0.3
        assert req.semantic_weight == 0.7

    def test_search_request_validation(self):
        with pytest.raises(ValueError):
            SearchRequest(query="", top_k=10)  # Empty query

        with pytest.raises(ValueError):
            SearchRequest(query="test", top_k=101)  # Above maximum
