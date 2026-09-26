from __future__ import annotations

import logging
import uuid
from typing import Any

from packages.domain.config import get_settings
from packages.retrieval.schemas import EvidenceHit, SearchType
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)


def _point_id(chunk_id: str) -> str:
    """Derive a deterministic Qdrant-compatible UUID from a chunk_id.

    Qdrant point ids must be UUID or int; chunk_ids are human-readable
    strings like ``{paper_id}-p{page}-c{n}``, so map them via UUID5.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantStore:
    def __init__(self, collection_name: str = "papers"):
        settings = get_settings()
        self.collection_name = collection_name
        self._client = QdrantClient(url=settings.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self, dimension: int | None = None) -> None:
        dim = dimension or get_settings().embedding_dimension
        try:
            self._client.get_collection(self.collection_name)
        except UnexpectedResponse:
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=dim,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="paper_id",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="project_id",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="year",
                field_schema=qdrant_models.PayloadSchemaType.INTEGER,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="author",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks or not embeddings:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        dimension = (
            len(embeddings[0])
            if embeddings and embeddings[0]
            else get_settings().embedding_dimension
        )
        try:
            self._client.get_collection(self.collection_name)
        except UnexpectedResponse:
            self._ensure_collection(dimension=dimension)
        points: list[qdrant_models.PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point = qdrant_models.PointStruct(
                id=_point_id(str(chunk["chunk_id"])),
                vector=embedding,
                payload={
                    "paper_id": str(chunk["paper_id"]),
                    "project_id": str(chunk.get("project_id", "")),
                    "page_number": chunk["page_number"],
                    "section_label": chunk.get("section_label"),
                    "text": chunk["text"],
                    "token_count": chunk["token_count"],
                    "year": chunk.get("year"),
                    "author": chunk.get("author"),
                    "title": chunk.get("title"),
                    "metadata": chunk.get("metadata", {}),
                },
            )
            points.append(point)

        self._client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def delete_paper_chunks(self, paper_id: uuid.UUID | str) -> None:
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="paper_id",
                            match=qdrant_models.MatchValue(value=str(paper_id)),
                        )
                    ]
                )
            ),
            wait=True,
        )

    def search_semantic(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[EvidenceHit]:
        query_filter = self._build_filter(filters) if filters else None

        response = self._client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        return self._results_to_hits(response.points, SearchType.SEMANTIC)

    def search_bm25(
        self,
        query_text: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[EvidenceHit]:
        query_filter = self._build_filter(filters) if filters else None

        try:
            document = qdrant_models.Document(text=query_text, model="qdrant/bm25")
        except Exception:
            logger.warning("BM25 Document query unavailable; returning no Qdrant BM25 hits")
            return []
        response = self._client.query_points(
            collection_name=self.collection_name,
            query=document,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        return self._results_to_hits(response.points, SearchType.BM25)

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 10,
        bm25_weight: float = 0.5,
        semantic_weight: float = 0.5,
        filters: dict[str, Any] | None = None,
    ) -> list[EvidenceHit]:
        semantic_hits = self.search_semantic(query_embedding, top_k * 2, filters)
        bm25_hits = self.search_bm25(query_text, top_k * 2, filters)

        combined = self._combine_hits(semantic_hits, bm25_hits, semantic_weight, bm25_weight)
        return combined[:top_k]

    def _build_filter(self, filters: dict[str, Any]) -> qdrant_models.Filter | None:
        must: list[Any] = []

        if "paper_ids" in filters and filters["paper_ids"]:
            must.append(
                qdrant_models.FieldCondition(
                    key="paper_id",
                    match=qdrant_models.MatchAny(any=[str(pid) for pid in filters["paper_ids"]]),
                )
            )

        if "project_id" in filters and filters["project_id"]:
            must.append(
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=str(filters["project_id"])),
                )
            )

        if "year_from" in filters and filters["year_from"]:
            must.append(
                qdrant_models.FieldCondition(
                    key="year",
                    range=qdrant_models.Range(gte=filters["year_from"]),
                )
            )

        if "year_to" in filters and filters["year_to"]:
            must.append(
                qdrant_models.FieldCondition(
                    key="year",
                    range=qdrant_models.Range(lte=filters["year_to"]),
                )
            )

        if "author" in filters and filters["author"]:
            must.append(
                qdrant_models.FieldCondition(
                    key="author",
                    match=qdrant_models.MatchText(text=filters["author"]),
                )
            )

        return qdrant_models.Filter(must=must) if must else None

    def _results_to_hits(self, results: list[Any], search_type: SearchType) -> list[EvidenceHit]:
        hits: list[EvidenceHit] = []
        for result in results:
            payload = result.payload or {}
            paper_id = payload.get("paper_id")
            text = payload.get("text")
            if not paper_id or not text:
                continue
            try:
                paper_uuid = uuid.UUID(str(paper_id))
            except ValueError:
                continue
            page_number = payload.get("page_number", 1)
            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                page_number = 1
            try:
                score = float(result.score)
            except (TypeError, ValueError):
                score = 0.0
            metadata = payload.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            hit = EvidenceHit(
                evidence_id=f"ev_{result.id}",
                paper_id=paper_uuid,
                paper_title=str(payload.get("title", "Unknown")),
                page_number=page_number,
                section_label=payload.get("section_label"),
                text=str(text),
                score=score,
                search_type=search_type,
                metadata=metadata,
            )
            hits.append(hit)
        return hits

    def _combine_hits(
        self,
        semantic_hits: list[EvidenceHit],
        bm25_hits: list[EvidenceHit],
        semantic_weight: float,
        bm25_weight: float,
    ) -> list[EvidenceHit]:
        hit_map: dict[str, EvidenceHit] = {}

        for hit in semantic_hits:
            key = f"{hit.paper_id}-{hit.page_number}-{hit.text[:50]}"
            weighted = hit.model_copy()
            weighted.score = hit.score * semantic_weight
            hit_map[key] = weighted

        for hit in bm25_hits:
            key = f"{hit.paper_id}-{hit.page_number}-{hit.text[:50]}"
            if key in hit_map:
                hit_map[key].score += hit.score * bm25_weight
                hit_map[key].search_type = SearchType.HYBRID
            else:
                weighted = hit.model_copy()
                weighted.score = hit.score * bm25_weight
                weighted.search_type = SearchType.HYBRID
                hit_map[key] = weighted

        combined = list(hit_map.values())
        combined.sort(key=lambda h: h.score, reverse=True)
        return combined

    def get_collection_info(self) -> dict[str, Any]:
        info = self._client.get_collection(self.collection_name)
        vectors_count = getattr(info, "indexed_vectors_count", None)
        if vectors_count is None:
            vectors_count = getattr(info, "vectors_count", 0) or 0
        return {
            "vectors_count": vectors_count or 0,
            "points_count": info.points_count or 0,
            "status": str(info.status),
        }


_qdrant_store: QdrantStore | None = None


def get_qdrant_store() -> QdrantStore:
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantStore()
    return _qdrant_store
