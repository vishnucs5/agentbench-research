from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TEvent = TypeVar("TEvent", bound="BaseEvent")
EventHandler = Callable[[Any], Awaitable[None]]


class BaseEvent(BaseModel):
    """Base event payload for domain events."""

    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str


class PaperUploadedEvent(BaseEvent):
    event_type: str = "paper.uploaded"
    paper_id: UUID
    project_id: UUID
    filename: str
    file_size_bytes: int


class PaperIndexedEvent(BaseEvent):
    event_type: str = "paper.indexed"
    paper_id: UUID
    project_id: UUID
    chunk_count: int
    vector_indexed: bool
    bm25_indexed: bool


class ClaimExtractedEvent(BaseEvent):
    event_type: str = "claim.extracted"
    paper_id: UUID
    claim_id: UUID
    claim_type: str
    confidence: float


class VerificationCompletedEvent(BaseEvent):
    event_type: str = "verification.completed"
    claim_id: UUID
    verdict: str
    confidence: float


class PlagiarismCheckedEvent(BaseEvent):
    event_type: str = "plagiarism.checked"
    check_id: UUID
    user_id: UUID
    similarity_score: float
    originality_score: float


class EventBus:
    """In-memory asynchronous event bus supporting publish-subscribe pattern."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._history: list[BaseEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe an asynchronous handler to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event asynchronously to all registered subscribers."""
        self._history.append(event)
        handlers = list(self._subscribers.get(event.event_type, []))
        # Also notify wildcard subscribers
        wildcard_handlers = list(self._subscribers.get("*", []))
        all_handlers = handlers + wildcard_handlers

        if not all_handlers:
            return

        async def _run_handler(h: EventHandler) -> None:
            try:
                await h(event)
            except Exception as e:
                logger.error(
                    "Error executing event handler %s for %s: %s",
                    getattr(h, "__name__", str(h)),
                    event.event_type,
                    e,
                    exc_info=True,
                )

        await asyncio.gather(*[_run_handler(h) for h in all_handlers])

    def get_history(self, event_type: str | None = None) -> list[BaseEvent]:
        """Retrieve recent events, optionally filtered by event type."""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.event_type == event_type]

    def clear(self) -> None:
        """Reset subscribers and event history."""
        self._subscribers.clear()
        self._history.clear()


_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the application event bus singleton."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """Reset the global event bus."""
    global _global_event_bus
    if _global_event_bus is not None:
        _global_event_bus.clear()
    _global_event_bus = None
