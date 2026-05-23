import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active.setdefault(channel, set()).add(websocket)
        logger.info("websocket_connected", channel=channel)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            if channel in self.active:
                self.active[channel].discard(websocket)
                if not self.active[channel]:
                    del self.active[channel]

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self.active.get(channel, set()))
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel, ws)


manager = ConnectionManager()


def org_channel(org_id: UUID | str) -> str:
    return f"org:{org_id}"


def dashboard_channel(dashboard_id: UUID | str) -> str:
    return f"dashboard:{dashboard_id}"
