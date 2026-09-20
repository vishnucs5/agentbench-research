from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class ModelResponse:
    content: str
    usage: dict[str, int] | None = None
    model: str | None = None
    finish_reason: str | None = None


class ModelProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class ModelProfile(BaseModel):
    name: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: int = 60
