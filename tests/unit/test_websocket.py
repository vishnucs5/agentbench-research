"""Tests for WebSocket manager."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from packages.websocket.manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


def test_initial_state(manager):
    assert manager.get_connection_count("project1") == 0


@pytest.mark.asyncio
async def test_connect(manager):
    websocket = AsyncMock()
    await manager.connect(websocket, "project1")
    assert manager.get_connection_count("project1") == 1
    websocket.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_multiple_clients(manager):
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect(ws1, "project1")
    await manager.connect(ws2, "project1")
    assert manager.get_connection_count("project1") == 2


@pytest.mark.asyncio
async def test_connect_different_projects(manager):
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect(ws1, "project1")
    await manager.connect(ws2, "project2")
    assert manager.get_connection_count("project1") == 1
    assert manager.get_connection_count("project2") == 1


def test_disconnect(manager):
    ws = MagicMock()
    manager._connections["project1"] = [ws]
    manager.disconnect(ws, "project1")
    assert manager.get_connection_count("project1") == 0


def test_disconnect_removes_empty_project(manager):
    ws = MagicMock()
    manager._connections["project1"] = [ws]
    manager.disconnect(ws, "project1")
    assert "project1" not in manager._connections


def test_disconnect_only_removes_target(manager):
    ws1 = MagicMock()
    ws2 = MagicMock()
    manager._connections["project1"] = [ws1, ws2]
    manager.disconnect(ws1, "project1")
    assert manager.get_connection_count("project1") == 1
    assert ws2 in manager._connections["project1"]


def test_disconnect_nonexistent_project(manager):
    ws = MagicMock()
    manager.disconnect(ws, "nonexistent")
    assert manager.get_connection_count("nonexistent") == 0


@pytest.mark.asyncio
async def test_broadcast_to_project(manager):
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    manager._connections["project1"] = [ws1, ws2]
    message = {"type": "test", "data": "hello"}
    await manager.broadcast_to_project("project1", message)
    ws1.send_json.assert_awaited_once_with(message)
    ws2.send_json.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_to_empty_project(manager):
    await manager.broadcast_to_project("nonexistent", {"type": "test"})


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected(manager):
    ws_ok = AsyncMock()
    ws_bad = AsyncMock()
    ws_bad.send_json.side_effect = Exception("connection lost")
    manager._connections["project1"] = [ws_ok, ws_bad]
    await manager.broadcast_to_project("project1", {"type": "test"})
    ws_ok.send_json.assert_awaited_once()
    assert manager.get_connection_count("project1") == 1
    assert ws_ok in manager._connections["project1"]


@pytest.mark.asyncio
async def test_broadcast_run_update(manager):
    ws = AsyncMock()
    manager._connections["project1"] = [ws]
    run_data = {"run_id": "abc", "status": "completed"}
    await manager.broadcast_run_update("project1", run_data)
    ws.send_json.assert_awaited_once_with(
        {
            "type": "run_update",
            "data": run_data,
        }
    )


@pytest.mark.asyncio
async def test_broadcast_stats_update(manager):
    ws = AsyncMock()
    manager._connections["project1"] = [ws]
    await manager.broadcast_stats_update("project1")
    ws.send_json.assert_awaited_once_with(
        {
            "type": "stats_update",
            "data": {},
        }
    )


def test_get_connection_count_empty(manager):
    assert manager.get_connection_count("project1") == 0
