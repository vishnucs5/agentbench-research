from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends
from packages.domain.database import get_db_session
from packages.domain.models import PaperStatus
from packages.ingestion.parser import PDFParser, create_parser
from packages.ingestion.repository import PaperRepository
from packages.ingestion.schemas import (
    IngestionJobStatus,
    PaperIngestRequest,
    ParsedPaper,
)
from packages.ingestion.storage import StorageService, get_storage_service
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from packages.domain.config import Settings


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        storage: StorageService | None = None,
        parser: PDFParser | None = None,
    ):
        self._session = session
        self._storage = storage or get_storage_service()
        self._parser = parser or create_parser()
        self._repo = PaperRepository(session)
        self._jobs: dict[UUID, IngestionJobStatus] = {}

    async def ingest_upload(
        self,
        project_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
        request: PaperIngestRequest,
    ) -> tuple[UUID, str]:
        if content_type.lower().split(";")[0].strip() != "application/pdf":
            raise ValueError(f"Unsupported content type: {content_type}")

        settings = self._get_settings()
        max_size = settings.max_file_size_mb * 1024 * 1024
        if len(file_data) > max_size:
            raise ValueError(f"File too large: {len(file_data)} bytes (max {max_size})")

        sha256 = self._storage.compute_sha256(file_data)

        existing = await self._repo.get_by_sha256_for_project(sha256, project_id)
        if existing:
            return existing.id, "duplicate"

        storage_key = f"{project_id}/{sha256}.pdf"
        try:
            self._storage.upload_file(storage_key, file_data, content_type)
            paper = await self._repo.create_paper(
                project_id=project_id,
                title=request.title,
                authors=[{"name": a} for a in (request.authors or [])],
                year=request.year,
                source_url=str(request.source_url) if request.source_url else None,
                doi=request.doi,
                sha256=sha256,
                storage_key=storage_key,
                parser_version=self._parser.parser_version,
                status=PaperStatus.UPLOADED,
            )
        except Exception:
            try:
                self._storage.delete_file(storage_key)
            except Exception:
                pass
            raise

        job_id = uuid.uuid4()
        self._jobs[job_id] = IngestionJobStatus(
            job_id=job_id,
            paper_id=paper.id,
            status="queued",
            progress=0.0,
            current_step="queued",
            started_at=datetime.now(UTC),
        )

        return paper.id, "created"

    async def ingest_url(
        self,
        project_id: UUID,
        url: str,
        request: PaperIngestRequest,
    ) -> tuple[UUID, str]:
        raise NotImplementedError("URL ingestion not yet implemented")

    async def process_paper(self, paper_id: UUID) -> ParsedPaper:
        paper = await self._repo.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        await self._repo.update_status(paper_id, PaperStatus.PARSING)

        job_id = uuid.uuid4()
        self._jobs[job_id] = IngestionJobStatus(
            job_id=job_id,
            paper_id=paper_id,
            status="processing",
            progress=0.1,
            current_step="downloading",
            started_at=datetime.now(UTC),
        )

        try:
            pdf_data = await asyncio.to_thread(self._storage.download_file, paper.storage_key)

            self._jobs[job_id].progress = 0.3
            self._jobs[job_id].current_step = "parsing"

            parsed = await asyncio.to_thread(self._parser.parse, pdf_data)

            if parsed.sha256 != paper.sha256:
                raise ValueError("PDF hash mismatch after parsing")

            self._jobs[job_id].progress = 0.8
            self._jobs[job_id].current_step = "saving"

            await self._repo.save_parsed_paper(paper_id, parsed)
        except Exception as e:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = "failed"
                job.current_step = "failed"
                job.error = str(e)
                job.completed_at = datetime.now(UTC)
            await self._repo.update_status(paper_id, PaperStatus.FAILED)
            raise

        self._jobs[job_id].progress = 1.0
        self._jobs[job_id].status = "completed"
        self._jobs[job_id].current_step = "completed"
        self._jobs[job_id].completed_at = datetime.now(UTC)

        return parsed

    def get_job_status(self, job_id: UUID) -> IngestionJobStatus | None:
        return self._jobs.get(job_id)

    def _get_settings(self) -> Settings:
        from packages.domain.config import get_settings

        return get_settings()


def get_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IngestionService:
    return IngestionService(session)
