import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections per user.

    Simple in‑memory manager – suitable for a single‑process deployment.
    For a scaled setup you would replace this with Redis Pub/Sub or a
    dedicated message broker.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
        logger.debug(
            f"WebSocket connected for user {user_id}, total={len(self.active_connections[user_id])}"
        )

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        connections = self.active_connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.active_connections.pop(user_id, None)
            logger.debug(
                f"WebSocket disconnected for user {user_id}, remaining={len(connections)}"
            )

    async def send_personal_message(self, user_id: str, message: str) -> None:
        connections = self.active_connections.get(user_id, [])
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as exc:
                logger.error(f"Failed to send WS message to {user_id}: {exc}")

    async def broadcast(self, message: str) -> None:
        # fire‑and‑forget to all connections
        for user_id in list(self.active_connections):
            await self.send_personal_message(user_id, message)


# Global manager instance used throughout the app
manager = ConnectionManager()
