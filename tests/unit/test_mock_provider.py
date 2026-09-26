from __future__ import annotations

import json

import pytest
from packages.agent.mock_provider import MockProvider
from packages.agent.providers import ModelResponse
from pydantic import BaseModel


class TestResponse(BaseModel):
    answer: str
    confidence: float


@pytest.fixture
def mock_provider():
    return MockProvider(
        {
            "test prompt": json.dumps({"answer": "test answer", "confidence": 0.9}),
        }
    )


@pytest.mark.asyncio
async def test_mock_provider_complete(mock_provider: MockProvider):
    response = await mock_provider.complete(
        messages=[{"role": "user", "content": "test prompt"}],
        response_format=TestResponse,
    )

    assert isinstance(response, ModelResponse)
    assert json.loads(response.content) == {"answer": "test answer", "confidence": 0.9}
    assert response.model == "mock-model"
    assert response.finish_reason == "stop"
    assert response.usage is not None


@pytest.mark.asyncio
async def test_mock_provider_default_response(mock_provider: MockProvider):
    response = await mock_provider.complete(
        messages=[{"role": "user", "content": "unknown prompt"}],
        response_format=TestResponse,
    )

    assert isinstance(response, ModelResponse)
    parsed = TestResponse.model_validate_json(response.content)
    assert parsed.answer == "mock response"
    assert parsed.confidence == 0.5


@pytest.mark.asyncio
async def test_mock_provider_without_format(mock_provider: MockProvider):
    response = await mock_provider.complete(
        messages=[{"role": "user", "content": "test prompt"}],
    )

    assert isinstance(response, ModelResponse)
    assert json.loads(response.content) == {"answer": "test answer", "confidence": 0.9}


@pytest.mark.asyncio
async def test_mock_provider_embed(mock_provider: MockProvider):
    embeddings = await mock_provider.embed(["text1", "text2"])

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384


@pytest.mark.asyncio
async def test_mock_provider_call_log(mock_provider: MockProvider):
    await mock_provider.complete(messages=[{"role": "user", "content": "test prompt"}])
    await mock_provider.complete(messages=[{"role": "user", "content": "another prompt"}])

    log = mock_provider.get_call_log()
    assert len(log) == 2
    assert log[0]["messages"][0]["content"] == "test prompt"
    assert log[1]["messages"][0]["content"] == "another prompt"


@pytest.mark.asyncio
async def test_mock_provider_set_response(mock_provider: MockProvider):
    mock_provider.set_response("new prompt", "new response")

    response = await mock_provider.complete(
        messages=[{"role": "user", "content": "new prompt"}],
    )

    assert response.content == "new response"
