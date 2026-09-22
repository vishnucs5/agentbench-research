from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.domain.database import get_db_session
from packages.domain.models import Chunk, Paper, Project, User
from packages.retrieval.schemas import EvidenceHit, SearchRequest, SearchResponse, SearchType
from packages.retrieval.service import RetrievalService, get_retrieval_service
from packages.security.middleware import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/search", tags=["retrieval"])


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> None:
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.owner_id == current_user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )


async def _hydrate_local_index(
    service: RetrievalService,
    session: AsyncSession,
    project_id: UUID | None,
) -> None:
    """Rebuild the in-memory BM25 corpus from DB chunks when no vector store."""
    if service.qdrant is not None or service._bm25_corpus:
        return
    query = (
        select(Chunk, Paper)
        .join(Paper, Chunk.paper_id == Paper.id)
        .order_by(Chunk.paper_id)
        .limit(5000)
    )
    if project_id:
        query = query.where(Paper.project_id == project_id)
    rows = (await session.execute(query)).all()
    chunk_dicts = [
        {
            "chunk_id": str(chunk.id),
            "paper_id": str(chunk.paper_id),
            "project_id": str(paper.project_id),
            "paper_title": paper.title,
            "page_number": 1,
            "section_label": None,
            "text": chunk.text,
            "token_count": chunk.token_count,
            "metadata": dict(chunk.metadata_json or {}),
        }
        for chunk, paper in rows
    ]
    if chunk_dicts:
        service.rebuild_local_index(chunk_dicts)


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    if request.project_id is not None:
        await _require_owned_project(session, request.project_id, current_user)
    try:
        await _hydrate_local_index(service, session, request.project_id)
        return await service.search(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    request.search_type = SearchType.SEMANTIC
    return await search(request, current_user, service, session)


@router.post("/bm25", response_model=SearchResponse)
async def bm25_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    request.search_type = SearchType.BM25
    return await search(request, current_user, service, session)


@router.get("/evidence/{evidence_id}", response_model=EvidenceHit)
async def get_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
) -> EvidenceHit:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Evidence lookup by ID not yet implemented",
    )


@router.get("/project/{project_id}/stats")
async def get_project_index_stats(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    await _require_owned_project(session, project_id, current_user)
    qdrant = service.qdrant
    if qdrant is None:
        return {
            "project_id": str(project_id),
            "total_chunks": 0,
            "collection_status": "unavailable",
        }
    info = qdrant.get_collection_info() or {}
    return {
        "project_id": str(project_id),
        "total_chunks": info.get("points_count", 0),
        "collection_status": info.get("status"),
    }
