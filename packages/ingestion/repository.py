from __future__ import annotations

from typing import Any
from uuid import UUID

from packages.domain.models import Paper, PaperPage, PaperStatus
from packages.ingestion.schemas import ParsedPaper
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class PaperRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_paper(
        self,
        project_id: UUID,
        title: str | None,
        authors: list[dict[str, Any]],
        year: int | None,
        source_url: str | None,
        doi: str | None,
        sha256: str,
        storage_key: str,
        parser_version: str,
        status: PaperStatus = PaperStatus.UPLOADED,
    ) -> Paper:
        paper = Paper(
            project_id=project_id,
            title=title or "Untitled",
            authors_json=authors,
            year=year,
            source_url=source_url,
            doi=doi,
            sha256=sha256,
            storage_key=storage_key,
            parser_version=parser_version,
            status=status,
        )
        self._session.add(paper)
        await self._session.flush()
        return paper

    async def get_by_sha256(self, sha256: str) -> Paper | None:
        result = await self._session.execute(select(Paper).where(Paper.sha256 == sha256))
        return result.scalar_one_or_none()

    async def get_by_sha256_for_project(self, sha256: str, project_id: UUID) -> Paper | None:
        result = await self._session.execute(
            select(Paper).where(Paper.sha256 == sha256, Paper.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, paper_id: UUID) -> Paper | None:
        result = await self._session.execute(
            select(Paper).options(selectinload(Paper.pages)).where(Paper.id == paper_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(
        self,
        project_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: PaperStatus | None = None,
    ) -> tuple[list[Paper], int]:
        query = select(Paper).where(Paper.project_id == project_id)
        if status:
            query = query.where(Paper.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self._session.scalar(count_query) or 0

        query = query.order_by(Paper.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(query)
        papers = list(result.scalars().all())

        return papers, total

    async def update_status(
        self,
        paper_id: UUID,
        status: PaperStatus,
        error: str | None = None,
    ) -> Paper | None:
        paper = await self.get_by_id(paper_id)
        if not paper:
            return None
        paper.status = status
        if error:
            paper.error = error
        await self._session.flush()
        return paper

    async def save_parsed_paper(self, paper_id: UUID, parsed: ParsedPaper) -> Paper:
        paper = await self.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        paper.title = parsed.metadata.title or paper.title
        paper.authors_json = parsed.metadata.authors or paper.authors_json
        paper.year = parsed.metadata.year or paper.year
        paper.parser_version = parsed.parser_version
        paper.status = PaperStatus.PARSED

        # delete existing pages first to avoid uq_paper_page_number IntegrityError
        await self._session.execute(delete(PaperPage).where(PaperPage.paper_id == paper_id))

        for page_data in parsed.pages:
            page = PaperPage(
                paper_id=paper_id,
                page_number=page_data.page_number,
                text=page_data.text,
                section_label=page_data.section_label,
                ocr_used=page_data.ocr_used,
                parser_version=parsed.parser_version,
            )
            self._session.add(page)

        await self._session.flush()
        return paper

    async def delete_paper(self, paper_id: UUID) -> bool:
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False
        await self._session.delete(paper)
        await self._session.flush()
        return True
