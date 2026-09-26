from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from packages.retrieval.embeddings import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    @pytest.fixture
    def mock_model(self):
        with patch("packages.retrieval.embeddings.SentenceTransformer") as mock:
            model = MagicMock()
            model.get_sentence_embedding_dimension.return_value = 384
            model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
            mock.return_value = model
            yield model

    @pytest.fixture
    def service(self, mock_model):
        return EmbeddingService(model_name="test-model")

    def test_embedding_service_creation(self, service):
        assert service.model_name == "test-model"

    def test_embed(self, service, mock_model):
        texts = ["text one", "text two"]
        embeddings = service.embed(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384
        mock_model.encode.assert_called_once()

    def test_embed_empty(self, service):
        embeddings = service.embed([])
        assert embeddings == []

    def test_embed_single(self, service, mock_model):
        embedding = service.embed_single("single text")
        assert len(embedding) == 384

    def test_embed_batch(self, service, mock_model):
        texts = ["text " + str(i) for i in range(100)]
        # Mock should return correct number of embeddings
        import numpy as np

        mock_model.encode.return_value = np.array([[0.1] * 384] * 100)
        embeddings = service.embed_batch(texts, batch_size=32)
        assert len(embeddings) == 100
        assert all(len(e) == 384 for e in embeddings)

    def test_dimension_property(self, service, mock_model):
        dim = service.dimension
        assert dim == 384


class TestGetEmbeddingService:
    def test_singleton(self):
        with patch("packages.retrieval.embeddings.SentenceTransformer"):
            service1 = get_embedding_service()
            service2 = get_embedding_service()
            assert service1 is service2
