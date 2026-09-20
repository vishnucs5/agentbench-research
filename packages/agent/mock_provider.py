from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .providers import ModelProvider, ModelResponse


class MockProvider(ModelProvider):
    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self._call_log: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        self._call_log.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format.__name__ if response_format else None,
            }
        )

        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        for key, response in self._responses.items():
            if key in last_user_msg:
                content = response
                break
        else:
            content = self._default_response(response_format)

        if response_format is not None:
            try:
                parsed = response_format.model_validate_json(content)
                content = parsed.model_dump_json()
            except Exception:
                pass

        return ModelResponse(
            content=content,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            model=self.model_name,
            finish_reason="stop",
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    def _default_response(self, response_format: type[BaseModel] | None) -> str:
        if response_format is not None:
            fields = {}
            for name, field in response_format.model_fields.items():
                if field.annotation is str:
                    fields[name] = "mock response"
                elif field.annotation is int:
                    fields[name] = 42
                elif field.annotation is float:
                    fields[name] = 0.5
                elif field.annotation is bool:
                    fields[name] = True
                elif field.annotation is list:
                    fields[name] = []
                else:
                    fields[name] = {}
            return response_format(**fields).model_dump_json()
        return "Mock response"

    def get_call_log(self) -> list[dict[str, Any]]:
        return self._call_log.copy()

    def set_response(self, key: str, response: str) -> None:
        self._responses[key] = response
