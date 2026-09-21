"""WebSocket endpoint handler."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from packages.websocket.manager import ConnectionManager

router = APIRouter(tags=["websocket"])

# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            # Keep connection alive, receive pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
