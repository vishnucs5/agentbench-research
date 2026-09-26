"""WebSocket connection manager for live updates."""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # project_id -> list of websocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        await websocket.accept()
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str) -> None:
        if project_id in self._connections:
            self._connections[project_id] = [
                ws for ws in self._connections[project_id] if ws != websocket
            ]
            if not self._connections[project_id]:
                del self._connections[project_id]

    async def broadcast_to_project(self, project_id: str, message: dict[str, Any]) -> None:
        if project_id not in self._connections:
            return

        disconnected = []
        for websocket in self._connections[project_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws, project_id)

    async def broadcast_run_update(self, project_id: str, run_data: dict[str, Any]) -> None:
        await self.broadcast_to_project(
            project_id,
            {
                "type": "run_update",
                "data": run_data,
            },
        )

    async def broadcast_stats_update(self, project_id: str) -> None:
        await self.broadcast_to_project(
            project_id,
            {
                "type": "stats_update",
                "data": {},
            },
        )

    def get_connection_count(self, project_id: str) -> int:
        return len(self._connections.get(project_id, []))


ws_manager = ConnectionManager()
