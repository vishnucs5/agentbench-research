from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from packages.domain.models import Paper, PaperStatus
from packages.ingestion.repository import PaperRepository
from packages.ingestion.schemas import PaperMetadata, ParsedPage, ParsedPaper
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    return PaperRepository(mock_session)


@pytest.fixture
def sample_parsed_paper():
    return ParsedPaper(
        metadata=PaperMetadata(
            title="Test Paper",
            authors=[{"name": "Author One"}],
            year=2024,
        ),
        pages=[
            ParsedPage(page_number=1, text="Page 1 content", char_count=14, token_count=3),
            ParsedPage(page_number=2, text="Page 2 content", char_count=14, token_count=3),
        ],
        parser_version="1.0.0",
        sha256="abc123",
    )


class TestPaperRepository:
    @pytest.mark.asyncio
    async def test_create_paper(self, repository, mock_session):
        project_id = uuid4()
        paper = await repository.create_paper(
            project_id=project_id,
            title="Test Paper",
            authors=[{"name": "Author"}],
            year=2024,
            source_url="https://example.com/paper.pdf",
            doi="10.1234/test",
            sha256="abc123",
            storage_key="project/abc123.pdf",
            parser_version="1.0.0",
        )

        assert isinstance(paper, Paper)
        assert paper.project_id == project_id
        assert paper.title == "Test Paper"
        assert paper.sha256 == "abc123"
        assert paper.status == PaperStatus.UPLOADED
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_sha256(self, repository, mock_session):
        sha256 = "abc123"
        mock_paper = MagicMock(spec=Paper)
        mock_paper.sha256 = sha256

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_sha256(sha256)

        assert result == mock_paper
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_sha256_for_project(self, repository, mock_session):
        sha256 = "abc123"
        project_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result
        result = await repository.get_by_sha256_for_project(sha256, project_id)
        assert result == mock_paper
        mock_session.execute.assert_called_once()
        # project filter must be part of the query, bound to the right values
        stmt = mock_session.execute.call_args.args[0]
        sent = str(stmt)
        assert "project_id" in sent
        assert "sha256" in sent.lower()
        params = stmt.compile().params
        assert params.get("sha256_1") == sha256
        assert params.get("project_id_1") == project_id

    @pytest.mark.asyncio
    async def test_get_by_sha256_for_project_scoped(self, repository, mock_session):
        # same sha under a different project must not match: returns None
        sha256 = "abc123"
        project_a = uuid4()
        project_b = uuid4()
        mock_paper = MagicMock(spec=Paper)

        async def fake_execute(stmt):
            params = stmt.compile().params
            result = MagicMock()
            if params.get("sha256_1") == sha256 and params.get("project_id_1") == project_a:
                result.scalar_one_or_none.return_value = mock_paper
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute.side_effect = fake_execute
        assert await repository.get_by_sha256_for_project(sha256, project_a) is mock_paper
        assert await repository.get_by_sha256_for_project(sha256, project_b) is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session):
        paper_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_paper.id = paper_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(paper_id)

        assert result == mock_paper

    @pytest.mark.asyncio
    async def test_get_by_project(self, repository, mock_session):
        project_id = uuid4()
        mock_papers = [MagicMock(spec=Paper) for _ in range(3)]

        mock_session.scalar = AsyncMock(return_value=3)

        mock_papers_result = MagicMock()
        mock_papers_result.scalars.return_value.all.return_value = mock_papers
        mock_session.execute = AsyncMock(return_value=mock_papers_result)

        papers, total = await repository.get_by_project(project_id, page=1, page_size=20)

        assert papers == mock_papers
        assert total == 3
        mock_session.scalar.assert_called_once()
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status(self, repository, mock_session):
        paper_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_paper.id = paper_id
        mock_paper.status = PaperStatus.UPLOADED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result

        result = await repository.update_status(paper_id, PaperStatus.PARSING, error="Test error")

        assert result == mock_paper
        assert mock_paper.status == PaperStatus.PARSING
        assert mock_paper.error == "Test error"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_parsed_paper(self, repository, mock_session, sample_parsed_paper):
        paper_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_paper.id = paper_id
        mock_paper.pages = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result

        result = await repository.save_parsed_paper(paper_id, sample_parsed_paper)

        assert result == mock_paper
        assert mock_paper.title == "Test Paper"
        assert mock_paper.status == PaperStatus.PARSED
        assert mock_session.add.call_count == 2  # Two pages added
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_parsed_paper_idempotent(
        self, repository, mock_session, sample_parsed_paper
    ):
        paper_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_paper.id = paper_id
        mock_paper.pages = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result
        await repository.save_parsed_paper(paper_id, sample_parsed_paper)
        # first execute is get_by_id, second must be delete(PaperPage) for idempotency
        assert mock_session.execute.call_count >= 2
        delete_stmt = str(mock_session.execute.call_args_list[1].args[0])
        assert "paper_pages" in delete_stmt.lower() or "delete" in delete_stmt.lower()

    @pytest.mark.asyncio
    async def test_delete_paper(self, repository, mock_session):
        paper_id = uuid4()
        mock_paper = MagicMock(spec=Paper)
        mock_paper.id = paper_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_session.execute.return_value = mock_result

        result = await repository.delete_paper(paper_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_paper)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_paper_not_found(self, repository, mock_session):
        paper_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.delete_paper(paper_id)

        assert result is False
        mock_session.delete.assert_not_called()
