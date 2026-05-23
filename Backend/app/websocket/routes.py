import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_token
from app.websocket.manager import ConnectionManager, dashboard_channel, manager, org_channel

router = APIRouter(tags=["websocket"])


async def _redis_listener(org_id: str, local_manager: ConnectionManager) -> None:
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(f"org:{org_id}:events", f"org:{org_id}:dashboard")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            channel = message["channel"]
            data = json.loads(message["data"])
            if channel.endswith(":dashboard"):
                await local_manager.broadcast(
                    org_channel(org_id),
                    {"type": data.get("type", "dashboard.refresh"), "payload": data},
                )
            else:
                await local_manager.broadcast(
                    org_channel(org_id),
                    {"type": data.get("type", "event.ingested"), "payload": data},
                )
    finally:
        await pubsub.unsubscribe(f"org:{org_id}:events", f"org:{org_id}:dashboard")
        await client.close()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    org_id: str | None = Query(default=None),
    dashboard_id: str | None = Query(default=None),
):
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
    except ValueError:
        await websocket.close(code=4001)
        return

    resolved_org = org_id or payload.get("org_id")
    if not resolved_org:
        await websocket.close(code=4002)
        return

    channel = org_channel(resolved_org)
    await manager.connect(channel, websocket)

    dash_channel = None
    if dashboard_id:
        dash_channel = dashboard_channel(dashboard_id)
        await manager.connect(dash_channel, websocket)

    listener_task = asyncio.create_task(_redis_listener(resolved_org, manager))

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.startswith("subscribe:dashboard:"):
                dash_id = data.split(":")[-1]
                dash_channel = dashboard_channel(dash_id)
                await manager.connect(dash_channel, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
        await manager.disconnect(channel, websocket)
        if dash_channel:
            await manager.disconnect(dash_channel, websocket)
