from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

from packages.domain.config import get_settings
from packages.ingestion.schemas import ParsedPaper
from packages.retrieval.chunker import ChunkingService
from packages.retrieval.embeddings import EmbeddingService
from packages.retrieval.qdrant_store import QdrantStore
from packages.retrieval.schemas import SearchRequest, SearchResponse, SearchType
from rank_bm25 import BM25Okapi


class RetrievalService:
    def __init__(
        self,
        chunker: ChunkingService | None = None,
        embedder: EmbeddingService | None = None,
        qdrant: QdrantStore | None = None,
    ):
        self.chunker = chunker or ChunkingService()
        self.embedder = embedder or EmbeddingService()
        self.qdrant = qdrant or QdrantStore()
        self._bm25_index: BM25Okapi | None = None
        self._bm25_corpus: list[dict[str, Any]] = []

    async def index_paper(
        self,
        paper: ParsedPaper,
        paper_id: str,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = self.chunker.chunk_paper(paper, paper_id)

        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": chunk.chunk_id,
                "paper_id": str(chunk.paper_id),
                "project_id": project_id or "",
                "page_number": chunk.page_number,
                "section_label": chunk.section_label,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            if metadata:
                chunk_dict.update(metadata)
            chunk_dicts.append(chunk_dict)

        texts = [c["text"] for c in chunk_dicts]
        embeddings = self.embedder.embed_batch(texts)

        self.qdrant.upsert_chunks(chunk_dicts, embeddings)

        self._update_bm25_index(chunk_dicts)

        return {
            "chunk_count": len(chunks),
            "embedded_count": len(embeddings),
            "bm25_indexed": True,
        }

    def _update_bm25_index(self, chunk_dicts: list[dict[str, Any]]) -> None:
        new_texts = [c["text"] for c in chunk_dicts]
        tokenized = [self._tokenize(t) for t in new_texts]

        if self._bm25_index is None:
            self._bm25_corpus = chunk_dicts
            self._bm25_index = BM25Okapi(tokenized)
        else:
            self._bm25_corpus.extend(chunk_dicts)
            all_tokenized = [self._tokenize(c["text"]) for c in self._bm25_corpus]
            self._bm25_index = BM25Okapi(all_tokenized)

    def _tokenize(self, text: str) -> list[str]:
        import re
        return re.findall(r"\b\w+\b", text.lower())

    async def search(self, request: SearchRequest) -> SearchResponse:
        import time
        start_time = time.perf_counter()

        filters = {}
        if request.project_id:
            filters["project_id"] = request.project_id
        if request.paper_ids:
            filters["paper_ids"] = request.paper_ids
        if request.year_from:
            filters["year_from"] = request.year_from
        if request.year_to:
            filters["year_to"] = request.year_to
        if request.author:
            filters["author"] = request.author

        query_embedding = self.embedder.embed_single(request.query)

        if request.search_type == SearchType.SEMANTIC:
            hits = self.qdrant.search_semantic(query_embedding, request.top_k, filters)
        elif request.search_type == SearchType.BM25:
            hits = self.qdrant.search_bm25(request.query, request.top_k, filters)
        else:
            hits = self.qdrant.hybrid_search(
                request.query,
                query_embedding,
                request.top_k,
                request.bm25_weight,
                request.semantic_weight,
                filters,
            )

        hits = [h for h in hits if h.score >= request.score_threshold]

        not_enough = len(hits) == 0 or (hits and hits[0].score < 0.3)

        took_ms = int((time.perf_counter() - start_time) * 1000)

        return SearchResponse(
            hits=hits,
            total=len(hits),
            query=request.query,
            search_type=request.search_type,
            took_ms=took_ms,
            not_enough_evidence=not_enough,
        )

    def delete_paper(self, paper_id: str) -> None:
        self.qdrant.delete_paper_chunks(paper_id)
        self._bm25_corpus = [c for c in self._bm25_corpus if c["paper_id"] != paper_id]
        if self._bm25_corpus:
            all_tokenized = [self._tokenize(c["text"]) for c in self._bm25_corpus]
            self._bm25_index = BM25Okapi(all_tokenized)
        else:
            self._bm25_index = None

    def save_bm25_index(self, path: str | None = None) -> None:
        if path is None:
            settings = get_settings()
            path = f"{settings.gold_set_path}/bm25_index.pkl"

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"index": self._bm25_index, "corpus": self._bm25_corpus}, f)

    def load_bm25_index(self, path: str | None = None) -> bool:
        if path is None:
            settings = get_settings()
            path = f"{settings.gold_set_path}/bm25_index.pkl"

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._bm25_index = data["index"]
            self._bm25_corpus = data["corpus"]
            return True
        except FileNotFoundError:
            return False


_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
