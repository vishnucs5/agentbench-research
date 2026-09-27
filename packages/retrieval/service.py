from __future__ import annotations

import asyncio
import logging
import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.domain.config import get_settings
from packages.ingestion.schemas import ParsedPaper
from packages.retrieval.chunker import ChunkingService
from packages.retrieval.embeddings import EmbeddingService
from packages.retrieval.schemas import (
    EvidenceHit,
    SearchRequest,
    SearchResponse,
    SearchType,
)
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        chunker: ChunkingService | None = None,
        embedder: EmbeddingService | None = None,
        qdrant: Any | None = None,
    ) -> None:
        self.chunker = chunker or ChunkingService()
        self.embedder = embedder or EmbeddingService()
        self.qdrant = qdrant
        if self.qdrant is None:
            try:
                from packages.retrieval.qdrant_store import QdrantStore

                self.qdrant = QdrantStore()
            except Exception as e:
                logger.warning("Qdrant unavailable (%s); using local BM25 only", e)
                self.qdrant = None
        self._bm25_index: BM25Okapi | None = None
        self._bm25_corpus: list[dict[str, Any]] = []
        self._tokenized_corpus: list[list[str]] = []
        try:
            self.load_bm25_index()
        except Exception as e:
            logger.warning("Could not load persisted BM25 index (%s)", e)

    async def index_paper(
        self,
        paper: ParsedPaper,
        paper_id: str,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = self.chunker.chunk_paper(paper, paper_id)  # type: ignore[arg-type]

        paper_title = "Unknown"
        try:
            candidate = paper.metadata.title if paper.metadata else None
            if candidate:
                paper_title = candidate
            elif metadata:
                candidate = metadata.get("paper_title") or metadata.get("title")
                if candidate:
                    paper_title = str(candidate)
        except Exception:
            pass

        allowed = {
            "chunk_id",
            "paper_id",
            "project_id",
            "page_number",
            "section_label",
            "text",
            "token_count",
            "metadata",
        }
        safe_meta = {
            k: v for k, v in (metadata or {}).items() if k not in allowed or k == "paper_title"
        }

        chunk_dicts: list[dict[str, Any]] = []
        for chunk in chunks:
            chunk_dict: dict[str, Any] = {
                "chunk_id": chunk.chunk_id,
                "paper_id": str(chunk.paper_id),
                "project_id": project_id or "",
                "page_number": chunk.page_number,
                "section_label": chunk.section_label,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
                "paper_title": paper_title,
                "title": paper_title,
            }
            chunk_dict.update(safe_meta)
            chunk_dicts.append(chunk_dict)

        texts: list[str] = [str(c["text"]) for c in chunk_dicts]
        embeddings: list[list[float]] = []
        embedded = False
        try:
            if texts:
                embeddings = await asyncio.to_thread(self.embedder.embed_batch, texts)
            else:
                embeddings = []
            embedded = True
        except Exception as e:
            logger.warning("Embedding failed, indexing text-only (%s)", e)

        assert len(chunk_dicts) == len(embeddings) or not embedded, "embedding count mismatch"

        qdrant_indexed = False
        if self.qdrant is not None and embedded:
            try:
                self.qdrant.upsert_chunks(chunk_dicts, embeddings)
                qdrant_indexed = True
            except Exception as e:
                logger.warning("Qdrant upsert failed (%s)", e)

        bm25_indexed = False
        try:
            self._update_bm25_index(chunk_dicts)
            self.save_bm25_index()
            bm25_indexed = True
        except Exception as e:
            logger.warning("Could not persist BM25 index (%s)", e)

        return {
            "chunk_count": len(chunks),
            "embedded_count": len(embeddings),
            "bm25_indexed": bm25_indexed,
            "vector_indexed": qdrant_indexed,
        }

    def _update_bm25_index(self, chunk_dicts: list[dict[str, Any]]) -> None:
        # Dedup by chunk_id so re-indexing never duplicates the corpus.
        incoming_by_id: dict[str, dict[str, Any]] = {}
        for c in chunk_dicts:
            incoming_by_id[str(c.get("chunk_id", ""))] = c
        deduped_incoming = list(incoming_by_id.values())
        incoming_ids = set(incoming_by_id.keys())

        # Ensure tokenized cache is aligned with corpus
        if len(self._tokenized_corpus) != len(self._bm25_corpus):
            self._tokenized_corpus = [
                self._tokenize(str(c.get("text", ""))) for c in self._bm25_corpus
            ]

        if incoming_ids:
            kept_corpus: list[dict[str, Any]] = []
            kept_tokens: list[list[str]] = []
            for doc, toks in zip(self._bm25_corpus, self._tokenized_corpus, strict=True):
                if str(doc.get("chunk_id", "")) not in incoming_ids:
                    kept_corpus.append(doc)
                    kept_tokens.append(toks)
            self._bm25_corpus = kept_corpus
            self._tokenized_corpus = kept_tokens

        new_texts = [str(c.get("text", "")) for c in deduped_incoming]
        new_tokenized = [self._tokenize(t) for t in new_texts]

        self._bm25_corpus.extend(deduped_incoming)
        self._tokenized_corpus.extend(new_tokenized)

        if self._tokenized_corpus:
            self._bm25_index = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25_index = None

    def _tokenize(self, text: str) -> list[str]:
        import re

        return re.findall(r"\b\w+\b", text.lower())

    async def search(self, request: SearchRequest) -> SearchResponse:
        import time

        start_time = time.perf_counter()

        filters: dict[str, Any] = {}
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

        if self._bm25_index is None:
            try:
                self.load_bm25_index()
            except Exception as e:
                logger.warning("Could not load persisted BM25 index (%s)", e)

        hits: list[EvidenceHit] = []
        if request.search_type == SearchType.BM25:
            hits = self._search_with_fallback(
                lambda: (
                    self.qdrant.search_bm25(request.query, request.top_k, filters)
                    if self.qdrant is not None
                    else self.search_bm25_local(request.query, request.top_k, filters)
                ),
                lambda: self.search_bm25_local(request.query, request.top_k, filters),
            )
        else:
            query_embedding: list[float] | None = None
            try:
                query_embedding = await asyncio.to_thread(self.embedder.embed_single, request.query)
            except Exception as e:
                logger.warning("Query embedding failed (%s)", e)
            if query_embedding is not None and self.qdrant is not None:
                try:
                    if request.search_type == SearchType.SEMANTIC:
                        hits = self.qdrant.search_semantic(query_embedding, request.top_k, filters)
                    else:
                        hits = self.qdrant.hybrid_search(
                            request.query,
                            query_embedding,
                            request.top_k,
                            request.bm25_weight,
                            request.semantic_weight,
                            filters,
                        )
                except Exception as e:
                    logger.warning("Vector search failed, falling back to local BM25 (%s)", e)
                    hits = self.search_bm25_local(request.query, request.top_k, filters)
            else:
                hits = self.search_bm25_local(request.query, request.top_k, filters)

        hits = [h for h in hits if h.score >= request.score_threshold]

        not_enough = len(hits) == 0 or (bool(hits) and hits[0].score < request.score_threshold)

        took_ms = int((time.perf_counter() - start_time) * 1000)

        return SearchResponse(
            hits=hits,
            total=len(hits),
            query=request.query,
            search_type=request.search_type,
            took_ms=took_ms,
            not_enough_evidence=not_enough,
        )

    @staticmethod
    def _search_with_fallback(
        primary: Callable[[], list[EvidenceHit]],
        fallback: Callable[[], list[EvidenceHit]],
    ) -> list[EvidenceHit]:
        try:
            return primary()
        except Exception as e:
            logger.warning("Primary search failed, using local BM25 fallback (%s)", e)
            return fallback()

    def _filter_corpus(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        corpus = self._bm25_corpus
        project_id = str(filters.get("project_id") or "")
        paper_ids = {str(p) for p in (filters.get("paper_ids") or [])}
        if project_id:
            corpus = [c for c in corpus if str(c.get("project_id", "")) == project_id]
        if paper_ids:
            corpus = [c for c in corpus if str(c.get("paper_id", "")) in paper_ids]
        return corpus

    def search_bm25_local(
        self, query: str, top_k: int, filters: dict[str, Any] | None = None
    ) -> list[EvidenceHit]:
        """Keyword search over the local BM25 corpus (no Qdrant/embeddings)."""

        filters = filters or {}
        corpus = self._filter_corpus(filters)
        if not corpus or self._bm25_index is None:
            return []
        tokenized = [self._tokenize(str(c.get("text", ""))) for c in corpus]
        index = BM25Okapi(tokenized)
        q_tokens = self._tokenize(query)
        scores = index.get_scores(q_tokens)
        ranked = sorted(zip(corpus, scores, strict=True), key=lambda x: x[1], reverse=True)[:top_k]
        hits: list[EvidenceHit] = []
        for chunk, score in ranked:
            chunk_tokens = set(self._tokenize(str(chunk.get("text", ""))))
            matched_terms = [t for t in q_tokens if t in chunk_tokens]
            final_score = float(score)
            if final_score <= 0:
                if not matched_terms:
                    continue
                final_score = round(len(matched_terms) / max(len(q_tokens), 1), 4)
            try:
                paper_uuid = UUID(str(chunk.get("paper_id", "")))
            except ValueError:
                continue
            hits.append(
                EvidenceHit(
                    evidence_id=str(chunk.get("chunk_id", "")),
                    paper_id=paper_uuid,
                    paper_title=str(chunk.get("paper_title") or chunk.get("title") or "Unknown"),
                    page_number=int(chunk.get("page_number", 1)),
                    section_label=chunk.get("section_label"),
                    text=str(chunk.get("text", "")),
                    score=final_score,
                    search_type=SearchType.BM25,
                    metadata=dict(chunk.get("metadata") or {}),
                )
            )
        return hits

    def rebuild_local_index(self, chunk_dicts: list[dict[str, Any]]) -> None:
        """Replace the in-memory BM25 corpus (e.g. after loading chunks from DB)."""
        self._bm25_corpus = list(chunk_dicts)
        if chunk_dicts:
            tokenized = [self._tokenize(str(c.get("text", ""))) for c in chunk_dicts]
            self._bm25_index = BM25Okapi(tokenized)
        else:
            self._bm25_index = None

    def delete_paper(self, paper_id: str) -> None:
        if self.qdrant is not None:
            try:
                self.qdrant.delete_paper_chunks(paper_id)
            except Exception as e:
                logger.warning("Qdrant delete failed (%s)", e)
        if len(self._tokenized_corpus) != len(self._bm25_corpus):
            self._tokenized_corpus = [
                self._tokenize(str(c.get("text", ""))) for c in self._bm25_corpus
            ]

        kept_corpus: list[dict[str, Any]] = []
        kept_tokens: list[list[str]] = []
        for doc, toks in zip(self._bm25_corpus, self._tokenized_corpus, strict=True):
            if str(doc.get("paper_id", "")) != str(paper_id):
                kept_corpus.append(doc)
                kept_tokens.append(toks)
        self._bm25_corpus = kept_corpus
        self._tokenized_corpus = kept_tokens

        if self._tokenized_corpus:
            self._bm25_index = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25_index = None

    def save_bm25_index(self, path: str | None = None) -> None:
        if path is None:
            settings = get_settings()
            path = settings.bm25_index_path

        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            with open(tmp, "wb") as f:
                pickle.dump(
                    {
                        "index": self._bm25_index,
                        "corpus": self._bm25_corpus,
                        "tokenized": self._tokenized_corpus,
                    },
                    f,
                )
            tmp.replace(target)
        except Exception as e:
            logger.warning("Could not persist BM25 index (%s)", e)
            raise

    def load_bm25_index(self, path: str | None = None) -> bool:
        if path is None:
            try:
                settings = get_settings()
                path = settings.bm25_index_path
            except Exception as e:
                logger.warning("Could not resolve BM25 index path (%s)", e)
                return False

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._bm25_index = data.get("index")
            self._bm25_corpus = data.get("corpus", [])
            cached_tokens = data.get("tokenized")
            if cached_tokens and len(cached_tokens) == len(self._bm25_corpus):
                self._tokenized_corpus = cached_tokens
            else:
                self._tokenized_corpus = [
                    self._tokenize(str(c.get("text", ""))) for c in self._bm25_corpus
                ]
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning("Could not load persisted BM25 index (%s)", e)
            return False


_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


def reset_retrieval_service() -> None:
    global _retrieval_service
    _retrieval_service = None
