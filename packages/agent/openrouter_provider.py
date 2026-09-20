from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from .providers import ModelProvider, ModelResponse


class OpenRouterProvider(ModelProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "anthropic/claude-3.5-sonnet",
        timeout_seconds: int = 60,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agentbench-research.local",
                "X-Title": "AgentBench-Research",
            },
            timeout=timeout_seconds,
        )

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = {"type": "json_schema", "json_schema": response_format.model_json_schema()}
            payload["strict"] = True

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        content = choice["message"]["content"] or ""
        usage = data.get("usage")

        return ModelResponse(
            content=content,
            usage=usage,
            model=data.get("model"),
            finish_reason=choice.get("finish_reason"),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": "text-embedding-3-small", "input": texts}
        response = await self._client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def close(self) -> None:
        await self._client.aclose()
