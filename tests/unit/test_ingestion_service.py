from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from packages.domain.models import PaperStatus
from packages.ingestion.schemas import PaperIngestRequest, PaperMetadata, ParsedPage, ParsedPaper
from packages.ingestion.service import IngestionService
from packages.ingestion.storage import StorageService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_storage():
    storage = MagicMock(spec=StorageService)
    storage.compute_sha256.return_value = "abc123"
    storage.upload_file.return_value = "project/abc123.pdf"
    storage.download_file.return_value = b"pdf content"
    return storage


@pytest.fixture
def mock_parser():
    parser = MagicMock()
    parser.parser_version = "1.0.0"
    return parser


@pytest.fixture
def service(mock_session, mock_storage, mock_parser):
    return IngestionService(mock_session, storage=mock_storage, parser=mock_parser)


@pytest.fixture
def sample_parsed_paper():
    return ParsedPaper(
        metadata=PaperMetadata(title="Test Paper", authors=[{"name": "Author"}], year=2024),
        pages=[ParsedPage(page_number=1, text="Content", char_count=7, token_count=2)],
        parser_version="1.0.0",
        sha256="abc123",
    )


class TestIngestionService:
    @pytest.mark.asyncio
    async def test_ingest_upload_success(self, service, mock_storage, mock_session):
        project_id = uuid4()
        file_data = b"pdf content"
        request = PaperIngestRequest(title="Test Paper", authors=["Author"], year=2024)

        with patch.object(service._repo, "get_by_sha256_for_project", return_value=None):
            with patch.object(service._repo, "create_paper") as mock_create:
                mock_paper = MagicMock()
                mock_paper.id = uuid4()
                mock_create.return_value = mock_paper

                paper_id, result = await service.ingest_upload(
                    project_id=project_id,
                    file_data=file_data,
                    filename="test.pdf",
                    content_type="application/pdf",
                    request=request,
                )

        assert result == "created"
        assert paper_id == mock_paper.id
        mock_storage.compute_sha256.assert_called_once_with(file_data)
        mock_storage.upload_file.assert_called_once()
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_upload_duplicate(self, service, mock_storage, mock_session):
        project_id = uuid4()
        file_data = b"pdf content"
        request = PaperIngestRequest()

        existing_paper = MagicMock()
        existing_paper.id = uuid4()

        with patch.object(service._repo, "get_by_sha256_for_project", return_value=existing_paper):
            paper_id, result = await service.ingest_upload(
                project_id=project_id,
                file_data=file_data,
                filename="test.pdf",
                content_type="application/pdf",
                request=request,
            )

        assert result == "duplicate"
        assert paper_id == existing_paper.id
        mock_storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_upload_invalid_content_type(self, service):
        project_id = uuid4()
        request = PaperIngestRequest()

        with pytest.raises(ValueError, match="Unsupported content type"):
            await service.ingest_upload(
                project_id=project_id,
                file_data=b"content",
                filename="test.txt",
                content_type="text/plain",
                request=request,
            )

    @pytest.mark.asyncio
    async def test_ingest_upload_file_too_large(self, service):
        project_id = uuid4()
        request = PaperIngestRequest()
        large_file = b"x" * (101 * 1024 * 1024)  # 101 MB

        with pytest.raises(ValueError, match="File too large"):
            await service.ingest_upload(
                project_id=project_id,
                file_data=large_file,
                filename="test.pdf",
                content_type="application/pdf",
                request=request,
            )

    @pytest.mark.asyncio
    async def test_process_paper_success(
        self, service, mock_storage, mock_parser, sample_parsed_paper
    ):
        paper_id = uuid4()

        mock_paper = MagicMock()
        mock_paper.id = paper_id
        mock_paper.storage_key = "project/abc123.pdf"
        mock_paper.sha256 = "abc123"

        with patch.object(service._repo, "get_by_id", return_value=mock_paper):
            with patch.object(service._repo, "update_status") as mock_update:
                with patch.object(service._repo, "save_parsed_paper") as mock_save:
                    mock_parser.parse.return_value = sample_parsed_paper

                    result = await service.process_paper(paper_id)

        assert result == sample_parsed_paper
        mock_storage.download_file.assert_called_once_with("project/abc123.pdf")
        mock_parser.parse.assert_called_once_with(b"pdf content")
        mock_update.assert_called_once_with(paper_id, PaperStatus.PARSING)
        mock_save.assert_called_once_with(paper_id, sample_parsed_paper)

    @pytest.mark.asyncio
    async def test_process_paper_not_found(self, service):
        paper_id = uuid4()

        with patch.object(service._repo, "get_by_id", return_value=None):
            with pytest.raises(ValueError, match="Paper .* not found"):
                await service.process_paper(paper_id)

    @pytest.mark.asyncio
    async def test_process_paper_hash_mismatch(
        self, service, mock_storage, mock_parser, sample_parsed_paper
    ):
        paper_id = uuid4()
        mock_paper = MagicMock()
        mock_paper.id = paper_id
        mock_paper.storage_key = "project/abc123.pdf"
        mock_paper.sha256 = "different_hash"

        with patch.object(service._repo, "get_by_id", return_value=mock_paper):
            with patch.object(service._repo, "update_status"):
                mock_parser.parse.return_value = sample_parsed_paper

                with pytest.raises(ValueError, match="PDF hash mismatch"):
                    await service.process_paper(paper_id)

    @pytest.mark.asyncio
    async def test_process_failure_sets_failed_not_parsing(
        self, service, mock_storage, mock_parser
    ):
        # upload corrupt PDF bytes, process must set status FAILED not stuck PARSING
        paper_id = uuid4()
        mock_paper = MagicMock()
        mock_paper.id = paper_id
        mock_paper.storage_key = "project/abc123.pdf"
        mock_paper.sha256 = "abc123"
        with patch.object(service._repo, "get_by_id", return_value=mock_paper):
            with patch.object(
                service._repo, "update_status", new_callable=AsyncMock
            ) as mock_update:
                mock_parser.parse.side_effect = ValueError("corrupt PDF")
                with pytest.raises(ValueError, match="corrupt PDF"):
                    await service.process_paper(paper_id)
                statuses = [
                    call.args[1] if len(call.args) > 1 else call.kwargs.get("status")
                    for call in mock_update.call_args_list
                ]
                assert PaperStatus.FAILED in statuses

    @pytest.mark.asyncio
    async def test_process_failure_marks_job_failed(self, service, mock_storage, mock_parser):
        paper_id = uuid4()
        mock_paper = MagicMock()
        mock_paper.id = paper_id
        mock_paper.storage_key = "project/abc123.pdf"
        mock_paper.sha256 = "abc123"
        with patch.object(service._repo, "get_by_id", return_value=mock_paper):
            with patch.object(service._repo, "update_status", new_callable=AsyncMock):
                mock_parser.parse.side_effect = ValueError("corrupt PDF")
                with pytest.raises(ValueError, match="corrupt PDF"):
                    await service.process_paper(paper_id)
        assert len(service._jobs) == 1
        job = next(iter(service._jobs.values()))
        assert job.status == "failed"
        assert job.current_step == "failed"
        assert job.error == "corrupt PDF"
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_ingest_upload_accepts_pdf_with_charset(self, service, mock_storage):
        project_id = uuid4()
        request = PaperIngestRequest(title="T")
        with patch.object(service._repo, "get_by_sha256_for_project", return_value=None):
            with patch.object(service._repo, "create_paper") as mock_create:
                mock_paper = MagicMock()
                mock_paper.id = uuid4()
                mock_create.return_value = mock_paper
                pid, result = await service.ingest_upload(
                    project_id, b"data", "a.pdf", "application/pdf; charset=binary", request
                )
                assert result == "created"
                assert pid == mock_paper.id

    @pytest.mark.asyncio
    async def test_ingest_upload_scoped_dedup(self, service, mock_storage):
        project_id = uuid4()
        request = PaperIngestRequest()
        with patch.object(
            service._repo, "get_by_sha256_for_project", return_value=None
        ) as mock_dedup:
            with patch.object(service._repo, "create_paper") as mock_create:
                mock_paper = MagicMock()
                mock_paper.id = uuid4()
                mock_create.return_value = mock_paper
                await service.ingest_upload(
                    project_id, b"data", "a.pdf", "application/pdf", request
                )
                mock_dedup.assert_called_once_with("abc123", project_id)

    @pytest.mark.asyncio
    async def test_ingest_upload_orphan_cleanup(self, service, mock_storage):
        project_id = uuid4()
        request = PaperIngestRequest()
        with patch.object(service._repo, "get_by_sha256_for_project", return_value=None):
            with patch.object(service._repo, "create_paper", side_effect=RuntimeError("db fail")):
                with pytest.raises(RuntimeError, match="db fail"):
                    await service.ingest_upload(
                        project_id, b"data", "a.pdf", "application/pdf", request
                    )
                mock_storage.delete_file.assert_called_once()

    def test_get_job_status(self, service):
        job_id = uuid4()
        paper_id = uuid4()

        from datetime import datetime

        from packages.ingestion.schemas import IngestionJobStatus

        job = IngestionJobStatus(
            job_id=job_id,
            paper_id=paper_id,
            status="completed",
            progress=1.0,
            current_step="done",
            started_at=datetime.utcnow(),
        )
        service._jobs[job_id] = job

        result = service.get_job_status(job_id)
        assert result == job

        result = service.get_job_status(uuid4())
        assert result is None
