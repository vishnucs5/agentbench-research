from __future__ import annotations

import time
from collections import defaultdict
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from packages.domain.config import get_settings
from packages.domain.database import get_db_session
from packages.domain.models import User
from packages.plagiarism.schemas import (
    PlagiarismCheckRequest,
    PlagiarismCheckResponse,
    PlagiarismCheckStatus,
    PlagiarismErrorResponse,
    PlagiarismListResponse,
    PlagiarismMatchResponse,
    PlagiarismReportResponse,
    SupportedFileTypesResponse,
)
from packages.plagiarism.service import PlagiarismService, get_plagiarism_service
from packages.security.middleware import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/plagiarism", tags=["plagiarism"])

# Simple in-memory rate limiter for plagiarism endpoints
_plagiarism_rate_store: dict[str, list[float]] = defaultdict(list)


async def _check_plagiarism_rate_limit(request: Request) -> None:
    """Rate limit plagiarism checks per IP/user.

    Uses settings plagiarism_rate_limit_per_minute / per_hour.
    Falls back to global RateLimitMiddleware if Redis unavailable.
    """
    settings = get_settings()
    per_min = settings.plagiarism_rate_limit_per_minute
    per_hour = settings.plagiarism_rate_limit_per_hour

    # Identify client
    forwarded = request.headers.get("X-Forwarded-For")
    client_id = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    # Also key by user if authenticated
    auth = request.headers.get("Authorization", "")
    key = f"{client_id}:{auth[:20]}" if auth else client_id

    now = time.time()
    window = _plagiarism_rate_store[key]
    # Remove entries older than 1 hour
    window[:] = [t for t in window if now - t < 3600]

    minute_count = sum(1 for t in window if now - t < 60)
    hour_count = len(window)

    if minute_count >= per_min:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {per_min} plagiarism checks per minute",
        )
    if hour_count >= per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {per_hour} plagiarism checks per hour",
        )
    window.append(now)


def _sanitize_text(text: str) -> str:
    """Sanitize uploaded text to remove control characters.

    HTML escaping is handled client-side; we only strip dangerous control chars here.
    """
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32 or ch in ("\r",))


@router.get(
    "/supported-types",
    response_model=SupportedFileTypesResponse,
    summary="Get supported file types for plagiarism checking",
)
async def get_supported_types(
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> SupportedFileTypesResponse:
    """Get list of supported file types and size limits."""
    settings = service.settings
    return SupportedFileTypesResponse(
        mime_types=settings.plagiarism_allowed_mime_types,
        extensions=[".txt", ".pdf", ".docx"],
        max_size_mb=settings.plagiarism_max_upload_size_mb,
    )


@router.post(
    "/check/text",
    response_model=PlagiarismCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Check text for plagiarism",
    responses={
        400: {"model": PlagiarismErrorResponse, "description": "Invalid request"},
        413: {"model": PlagiarismErrorResponse, "description": "Text too long"},
        422: {"model": PlagiarismErrorResponse, "description": "Validation error"},
    },
)
async def check_text(
    request: PlagiarismCheckRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> PlagiarismCheckResponse:
    """Check submitted text for potentially similar content.

    Submit plain text to compare against stored documents and external sources.
    Returns a check ID that can be used to retrieve the full report.
    """
    await _check_plagiarism_rate_limit(http_request)

    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text content is required",
        )

    # Validate text length
    max_chars = 1000000  # 1M characters
    if len(request.text) > max_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds maximum length of {max_chars} characters",
        )

    # Sanitize input: strip control chars
    sanitized_for_check = _sanitize_text(request.text.strip())

    result = await service.check_text(
        text=sanitized_for_check,
        user_id=current_user.id,
        project_id=request.project_id,
        consented_to_store=request.consented_to_store,
        threshold=request.threshold,
    )

    # Fetch full record to provide accurate timestamps
    check = await service.get_check_result(result.check_id, current_user.id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve check result",
        )

    return PlagiarismCheckResponse(
        id=check.id,
        user_id=check.user_id,
        project_id=check.project_id,
        source_filename=check.source_filename,
        source_mime_type=check.source_mime_type,
        source_size_bytes=check.source_size_bytes,
        status=check.status,
        overall_similarity=check.overall_similarity,
        originality_score=check.originality_score,
        total_matches=check.total_matches,
        provider_used=check.provider_used,
        error_message=check.error_message,
        consented_to_store=check.consented_to_store,
        created_at=check.created_at,
        completed_at=check.completed_at,
    )


@router.post(
    "/check/file",
    response_model=PlagiarismCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Check uploaded file for plagiarism",
    responses={
        400: {"model": PlagiarismErrorResponse, "description": "Invalid file or unsupported type"},
        413: {"model": PlagiarismErrorResponse, "description": "File too large"},
        415: {"model": PlagiarismErrorResponse, "description": "Unsupported media type"},
    },
)
async def check_file(
    http_request: Request,
    file: UploadFile = File(...),
    project_id: UUID | None = Form(None),
    threshold: float | None = Form(None),
    consented_to_store: bool = Form(False),
    current_user: User = Depends(get_current_user),
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> PlagiarismCheckResponse:
    """Upload and check a file for potentially similar content.

    Supported formats: .txt, .pdf, .docx
    Maximum file size: 10 MB (configurable)
    """
    await _check_plagiarism_rate_limit(http_request)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Read file content
    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    # Validate file size quickly
    settings = get_settings()
    max_bytes = settings.plagiarism_max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.plagiarism_max_upload_size_mb} MB",
        )

    try:
        result = await service.check_file(
            file_data=content,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
            project_id=project_id,
            consented_to_store=consented_to_store,
            threshold=threshold,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    check = await service.get_check_result(result.check_id, current_user.id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve check result",
        )

    return PlagiarismCheckResponse(
        id=check.id,
        user_id=check.user_id,
        project_id=check.project_id,
        source_filename=check.source_filename,
        source_mime_type=check.source_mime_type,
        source_size_bytes=check.source_size_bytes,
        status=check.status,
        overall_similarity=check.overall_similarity,
        originality_score=check.originality_score,
        total_matches=check.total_matches,
        provider_used=check.provider_used,
        error_message=check.error_message,
        consented_to_store=check.consented_to_store,
        created_at=check.created_at,
        completed_at=check.completed_at,
    )


@router.get(
    "/checks",
    response_model=PlagiarismListResponse,
    summary="List user's plagiarism checks",
)
async def list_checks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: PlagiarismCheckStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> PlagiarismListResponse:
    """List all plagiarism checks for the current user."""
    checks, total = await service.list_user_checks(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )

    return PlagiarismListResponse(
        checks=[
            PlagiarismCheckResponse(
                id=c.id,
                user_id=c.user_id,
                project_id=c.project_id,
                source_filename=c.source_filename,
                source_mime_type=c.source_mime_type,
                source_size_bytes=c.source_size_bytes,
                status=c.status,
                overall_similarity=c.overall_similarity,
                originality_score=c.originality_score,
                total_matches=c.total_matches,
                provider_used=c.provider_used,
                error_message=c.error_message,
                consented_to_store=c.consented_to_store,
                created_at=c.created_at,
                completed_at=c.completed_at,
            )
            for c in checks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/checks/{check_id}",
    response_model=PlagiarismReportResponse,
    summary="Get detailed plagiarism report",
    responses={
        404: {"model": PlagiarismErrorResponse, "description": "Check not found"},
    },
)
async def get_report(
    check_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> PlagiarismReportResponse:
    """Get detailed plagiarism report with all matches."""
    check = await service.get_check_result(check_id, current_user.id)

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plagiarism check not found",
        )

    matches = await service.get_check_matches(check_id, current_user.id)

    # Generate human-readable summary
    summary = _generate_summary(check, matches)

    return PlagiarismReportResponse(
        check=PlagiarismCheckResponse(
            id=check.id,
            user_id=check.user_id,
            project_id=check.project_id,
            source_filename=check.source_filename,
            source_mime_type=check.source_mime_type,
            source_size_bytes=check.source_size_bytes,
            status=check.status,
            overall_similarity=check.overall_similarity,
            originality_score=check.originality_score,
            total_matches=check.total_matches,
            provider_used=check.provider_used,
            error_message=check.error_message,
            consented_to_store=check.consented_to_store,
            created_at=check.created_at,
            completed_at=check.completed_at,
        ),
        matches=[
            PlagiarismMatchResponse(
                id=m.id,
                source_type=m.source_type,
                matched_text=m.matched_text,
                source_text=m.source_text,
                similarity_score=m.similarity_score,
                confidence_score=m.confidence_score,
                source_document_id=m.source_document_id,
                source_document_title=m.source_document_title,
                source_url=m.source_url,
                source_location=m.source_location,
                match_start_offset=m.match_start_offset,
                match_end_offset=m.match_end_offset,
                created_at=m.created_at,
            )
            for m in matches
        ],
        summary=summary,
    )


@router.delete(
    "/checks/{check_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a plagiarism check and its matches",
    responses={
        404: {"model": PlagiarismErrorResponse, "description": "Check not found"},
    },
)
async def delete_check(
    check_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a plagiarism check (only if user owns it)."""
    from packages.domain.models import PlagiarismCheck

    result = await session.execute(
        select(PlagiarismCheck).where(
            PlagiarismCheck.id == check_id,
            PlagiarismCheck.user_id == current_user.id,
        )
    )
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plagiarism check not found",
        )

    await session.delete(check)
    await session.commit()


def _generate_summary(check, matches) -> str:
    """Generate human-readable summary of plagiarism check results."""
    if check.status == PlagiarismCheckStatus.FAILED:
        return f"Check failed: {check.error_message or 'Unknown error'}"

    if check.total_matches == 0:
        return (
            "No potentially similar content detected. "
            "The submitted text appears to be original based on the sources checked."
        )

    # Categorize matches by similarity
    high = sum(1 for m in matches if m.similarity_score >= 0.7)
    medium = sum(1 for m in matches if 0.4 <= m.similarity_score < 0.7)
    low = sum(1 for m in matches if m.similarity_score < 0.4)

    parts = [
        f"Found {check.total_matches} potentially similar passage(s) "
        f"with an overall similarity of {check.overall_similarity:.1%}."
    ]

    if high:
        parts.append(
            f"{high} passage(s) show high similarity (≥70%), "
            "which may indicate direct copying or close paraphrasing."
        )
    if medium:
        parts.append(
            f"{medium} passage(s) show moderate similarity (40-70%), "
            "which may indicate paraphrasing or common phrases."
        )
    if low:
        parts.append(
            f"{low} passage(s) show low similarity (<40%), "
            "which may be coincidental or common terminology."
        )

    parts.append(
        "Note: Similarity scores indicate textual overlap, not necessarily plagiarism. "
        "Please review matches manually and consider context, citations, and fair use."
    )

    return " ".join(parts)
