from __future__ import annotations

from uuid import uuid4

import pytest
from packages.domain.events import (
    EventBus,
    PaperIndexedEvent,
    PaperUploadedEvent,
    get_event_bus,
    reset_event_bus,
)


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    async def on_paper_uploaded(evt: PaperUploadedEvent):
        received.append(evt.filename)

    bus.subscribe("paper.uploaded", on_paper_uploaded)

    paper_id = uuid4()
    project_id = uuid4()
    await bus.publish(
        PaperUploadedEvent(
            paper_id=paper_id,
            project_id=project_id,
            filename="intrusion_detection.pdf",
            file_size_bytes=1024,
        )
    )

    assert len(received) == 1
    assert received[0] == "intrusion_detection.pdf"
    assert len(bus.get_history()) == 1


@pytest.mark.asyncio
async def test_event_bus_wildcard_subscriber():
    bus = EventBus()
    events = []

    async def log_all(evt):
        events.append(evt.event_type)

    bus.subscribe("*", log_all)

    await bus.publish(
        PaperIndexedEvent(
            paper_id=uuid4(),
            project_id=uuid4(),
            chunk_count=12,
            vector_indexed=True,
            bm25_indexed=True,
        )
    )

    assert len(events) == 1
    assert events[0] == "paper.indexed"


@pytest.mark.asyncio
async def test_event_bus_error_isolation():
    bus = EventBus()
    processed = []

    async def failing_handler(evt):
        raise ValueError("handler crashed")

    async def healthy_handler(evt):
        processed.append(evt.filename)

    bus.subscribe("paper.uploaded", failing_handler)
    bus.subscribe("paper.uploaded", healthy_handler)

    # Publishing should not raise even if one handler fails
    await bus.publish(
        PaperUploadedEvent(
            paper_id=uuid4(),
            project_id=uuid4(),
            filename="safe.pdf",
            file_size_bytes=500,
        )
    )

    assert processed == ["safe.pdf"]
