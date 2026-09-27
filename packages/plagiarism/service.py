from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from packages.domain.config import get_settings
from packages.domain.database import get_session
from packages.domain.models import (
    PlagiarismCheck,
    PlagiarismCheckStatus,
    PlagiarismMatch,
    PlagiarismSourceType,
)
from packages.plagiarism.parser import DocumentParserFactory, create_parser
from packages.plagiarism.providers import (
    PlagiarismProvider,
    create_provider,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)


@dataclass
class PlagiarismServiceResult:
    """Result from the plagiarism service."""

    check_id: UUID
    status: PlagiarismCheckStatus
    overall_similarity: float
    originality_score: float
    total_matches: int
    provider_used: str
    error_message: str | None = None


class PlagiarismService:
    """Main service for orchestrating plagiarism checks."""

    def __init__(
        self,
        provider: PlagiarismProvider | None = None,
        parser_factory: DocumentParserFactory | None = None,
    ):
        self.provider = provider or create_provider("internal")
        self.parser_factory = parser_factory or create_parser()
        self.settings = get_settings()

    async def _run_and_persist_check(
        self,
        text: str,
        user_id: UUID,
        project_id: UUID | None,
        source_filename: str | None,
        source_mime_type: str,
        source_size_bytes: int,
        consented_to_store: bool,
        threshold: float | None,
    ) -> PlagiarismServiceResult:
        """Unified internal runner to execute plagiarism check and persist results."""
        effective_threshold = (
            threshold if threshold is not None else self.settings.plagiarism_similarity_threshold
        )
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        async with get_session() as session:
            check = PlagiarismCheck(
                user_id=user_id,
                project_id=project_id,
                source_text_hash=text_hash,
                source_filename=source_filename,
                source_mime_type=source_mime_type,
                source_size_bytes=source_size_bytes,
                status=PlagiarismCheckStatus.PROCESSING,
                consented_to_store=consented_to_store,
            )
            session.add(check)
            await session.flush()
            check_id = check.id

            try:
                # Run plagiarism check via configured provider
                result = await self.provider.check(
                    text=text,
                    session=session,
                    user_id=user_id,
                    project_id=project_id,
                    threshold=effective_threshold,
                )

                # Update check record with detection metrics
                check.status = (
                    PlagiarismCheckStatus.COMPLETED
                    if not result.error_message
                    else PlagiarismCheckStatus.FAILED
                )
                check.overall_similarity = result.overall_similarity
                check.originality_score = result.originality_score
                check.total_matches = result.total_matches
                check.provider_used = result.provider_used
                check.error_message = result.error_message
                check.completed_at = datetime.now(UTC)

                # Store matches if consented
                if consented_to_store and result.matches:
                    for match in result.matches:
                        match_record = PlagiarismMatch(
                            check_id=check_id,
                            source_type=PlagiarismSourceType.INTERNAL
                            if result.provider_used == "internal"
                            else PlagiarismSourceType.EXTERNAL_API,
                            matched_text=match.matched_text,
                            source_text=match.source_text,
                            similarity_score=match.similarity_score,
                            confidence_score=match.confidence,
                            source_document_title=match.source_text[:100]
                            if len(match.source_text) > 100
                            else match.source_text,
                            match_start_offset=match.match_start,
                            match_end_offset=match.match_end,
                        )
                        session.add(match_record)

                await session.commit()

                return PlagiarismServiceResult(
                    check_id=check_id,
                    status=check.status,
                    overall_similarity=result.overall_similarity,
                    originality_score=result.originality_score,
                    total_matches=result.total_matches,
                    provider_used=result.provider_used,
                    error_message=result.error_message,
                )

            except Exception as e:
                logger.error("Plagiarism check execution failed: %s", e, exc_info=True)
                check.status = PlagiarismCheckStatus.FAILED
                check.error_message = str(e)
                check.completed_at = datetime.now(UTC)
                await session.commit()

                return PlagiarismServiceResult(
                    check_id=check_id,
                    status=PlagiarismCheckStatus.FAILED,
                    overall_similarity=0.0,
                    originality_score=100.0,
                    total_matches=0,
                    provider_used=self.provider.get_name(),
                    error_message=str(e),
                )

    async def check_text(
        self,
        text: str,
        user_id: UUID,
        project_id: UUID | None = None,
        consented_to_store: bool = False,
        threshold: float | None = None,
    ) -> PlagiarismServiceResult:
        """Check plain text for plagiarism."""
        return await self._run_and_persist_check(
            text=text,
            user_id=user_id,
            project_id=project_id,
            source_filename=None,
            source_mime_type="text/plain",
            source_size_bytes=len(text.encode()),
            consented_to_store=consented_to_store,
            threshold=threshold,
        )

    async def check_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        user_id: UUID,
        project_id: UUID | None = None,
        consented_to_store: bool = False,
        threshold: float | None = None,
    ) -> PlagiarismServiceResult:
        """Check uploaded file for plagiarism."""
        # Validate file format and size
        if not self.parser_factory.is_supported(filename, mime_type):
            raise ValueError(f"Unsupported file type: {mime_type or filename}")

        max_size = self.settings.plagiarism_max_upload_size_mb * 1024 * 1024
        if len(file_data) > max_size:
            raise ValueError(
                f"File size exceeds maximum allowed ({self.settings.plagiarism_max_upload_size_mb} MB)"
            )

        # Extract text from document
        parser = self.parser_factory.get_parser(filename, mime_type)
        try:
            text = parser.parse(file_data, filename)
        except Exception as e:
            logger.error("Failed to parse file %s: %s", filename, e, exc_info=True)
            raise ValueError(f"Failed to extract text from file: {e}")

        if not text or not text.strip():
            raise ValueError("No readable text found in file")

        return await self._run_and_persist_check(
            text=text,
            user_id=user_id,
            project_id=project_id,
            source_filename=filename,
            source_mime_type=mime_type,
            source_size_bytes=len(file_data),
            consented_to_store=consented_to_store,
            threshold=threshold,
        )

    async def get_check_result(self, check_id: UUID, user_id: UUID) -> PlagiarismCheck | None:
        """Get plagiarism check result by ID."""
        async with get_session() as session:
            result = await session.execute(
                select(PlagiarismCheck).where(
                    PlagiarismCheck.id == check_id,
                    PlagiarismCheck.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_check_matches(self, check_id: UUID, user_id: UUID) -> list[PlagiarismMatch]:
        """Get matches for a plagiarism check."""
        async with get_session() as session:
            # Verify ownership
            check = await session.execute(
                select(PlagiarismCheck).where(
                    PlagiarismCheck.id == check_id,
                    PlagiarismCheck.user_id == user_id,
                )
            )
            if not check.scalar_one_or_none():
                return []

            result = await session.execute(
                select(PlagiarismMatch)
                .where(PlagiarismMatch.check_id == check_id)
                .order_by(PlagiarismMatch.similarity_score.desc())
            )
            return list(result.scalars().all())

    async def list_user_checks(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: PlagiarismCheckStatus | None = None,
    ) -> tuple[list[PlagiarismCheck], int]:
        """List plagiarism checks for a user."""
        async with get_session() as session:
            query = select(PlagiarismCheck).where(PlagiarismCheck.user_id == user_id)

            if status:
                query = query.where(PlagiarismCheck.status == status)

            # Get total count
            from sqlalchemy import func

            count_result = await session.execute(select(func.count()).select_from(query.subquery()))
            total = count_result.scalar() or 0

            # Get paginated results
            query = query.order_by(PlagiarismCheck.created_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            checks = result.scalars().all()

            return list(checks), total


_plagiarism_service: PlagiarismService | None = None


def get_plagiarism_service() -> PlagiarismService:
    """Get or create the global plagiarism service instance."""
    global _plagiarism_service
    if _plagiarism_service is None:
        settings = get_settings()
        # Auto-select provider: combined if external API configured, else internal
        # Mock is used explicitly in tests via dependency override
        if settings.plagiarism_api_key and settings.plagiarism_api_url:
            try:
                from packages.plagiarism.providers import (
                    CombinedProvider,
                    ExternalAPIProvider,
                    InternalProvider,
                )

                _plagiarism_service = PlagiarismService(
                    provider=CombinedProvider(
                        internal=InternalProvider(),
                        external=ExternalAPIProvider(),
                    )
                )
            except Exception:
                _plagiarism_service = PlagiarismService()
        else:
            _plagiarism_service = PlagiarismService()
    return _plagiarism_service


def reset_plagiarism_service() -> None:
    global _plagiarism_service
    _plagiarism_service = None
