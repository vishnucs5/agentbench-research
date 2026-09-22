from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from packages.ingestion.storage import StorageService, get_storage_service


class TestStorageService:
    @pytest.fixture
    def mock_minio_client(self):
        with patch("packages.ingestion.storage.Minio") as mock_minio:
            client = MagicMock()
            mock_minio.return_value = client
            client.bucket_exists.return_value = True
            yield client

    @pytest.fixture
    def storage_service(self, mock_minio_client):
        return StorageService()

    def test_compute_sha256(self, storage_service):
        data = b"test data"
        expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
        assert storage_service.compute_sha256(data) == expected

    def test_compute_sha256_empty(self, storage_service):
        data = b""
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert storage_service.compute_sha256(data) == expected

    def test_compute_sha256_stream(self, storage_service):
        data = b"stream test data"
        stream = io.BytesIO(data)
        sha256, returned_data = storage_service.compute_sha256_stream(stream)
        assert len(sha256) == 64
        assert returned_data == data

    def test_compute_sha256_stream_rewinds(self, storage_service):
        data = b"stream test data"
        stream = io.BytesIO(data)
        storage_service.compute_sha256_stream(stream)
        assert stream.tell() == 0
        assert stream.read() == data

    def test_ensure_bucket_creates_if_not_exists(self, mock_minio_client):
        mock_minio_client.bucket_exists.return_value = False
        StorageService()
        mock_minio_client.make_bucket.assert_called_once()

    def test_upload_file(self, storage_service, mock_minio_client):
        data = b"pdf content"
        object_key = "test/paper.pdf"
        result = storage_service.upload_file(object_key, data)
        assert result == object_key
        mock_minio_client.put_object.assert_called_once()

    def test_file_exists_true(self, storage_service, mock_minio_client):
        mock_minio_client.stat_object.return_value = MagicMock()
        assert storage_service.file_exists("test.pdf") is True

    def test_file_exists_false(self, storage_service, mock_minio_client):
        from minio.error import S3Error
        from urllib3 import HTTPResponse
        # S3Error constructor: (response, code, message, resource, request_id, host_id, bucket_name, object_name)
        response = HTTPResponse()
        response.status = 404
        error = S3Error(response, "NoSuchKey", "Not Found", "test", "test", "test")
        mock_minio_client.stat_object.side_effect = error
        assert storage_service.file_exists("missing.pdf") is False

    def test_get_presigned_url(self, storage_service, mock_minio_client):
        mock_minio_client.presigned_get_object.return_value = "http://presigned.url"
        url = storage_service.get_presigned_url("test.pdf", expires=3600)
        assert url == "http://presigned.url"
        mock_minio_client.presigned_get_object.assert_called_once_with(
            "papers", "test.pdf", expires=3600
        )


class TestGetStorageService:
    def test_singleton(self):
        with patch("packages.ingestion.storage.Minio"):
            service1 = get_storage_service()
            service2 = get_storage_service()
            assert service1 is service2
