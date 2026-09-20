from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.retrieval.schemas import EvidenceHit, SearchRequest, SearchResponse, SearchType
from packages.retrieval.service import RetrievalService, get_retrieval_service

router = APIRouter(prefix="/v1/search", tags=["retrieval"])


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
):
    try:
        return await service.search(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
):
    request.search_type = SearchType.SEMANTIC
    return await search(request, service)


@router.post("/bm25", response_model=SearchResponse)
async def bm25_search(
    request: SearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
):
    request.search_type = SearchType.BM25
    return await search(request, service)


@router.get("/evidence/{evidence_id}", response_model=EvidenceHit)
async def get_evidence(
    evidence_id: str,
    service: RetrievalService = Depends(get_retrieval_service),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Evidence lookup by ID not yet implemented",
    )


@router.get("/project/{project_id}/stats")
async def get_project_index_stats(
    project_id: UUID,
    service: RetrievalService = Depends(get_retrieval_service),
):
    qdrant = service.qdrant
    info = qdrant.get_collection_info()
    return {
        "project_id": str(project_id),
        "total_chunks": info.get("points_count", 0),
        "collection_status": info.get("status"),
    }
