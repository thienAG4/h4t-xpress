"""WebSocket endpoint. The access token is sent in the first message, not in the URL,
so it never ends up in proxy logs (SPEC §5.2).

Protocol:
  client -> {"type": "auth", "token": "<access token>"}
  server -> {"event": "ready", "data": {"channels": [...]}}
  server -> {"event": "<name>", "data": {...}}   for every published event
  client -> "ping" (any text) keeps the connection alive; server answers "pong"
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.modules.realtime.hub import hub_channel, realtime, user_channel

logger = logging.getLogger(__name__)

router = APIRouter()
AUTH_TIMEOUT_SECONDS = 10


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        message = await asyncio.wait_for(websocket.receive_json(), AUTH_TIMEOUT_SECONDS)
    except (TimeoutError, WebSocketDisconnect, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    claims = (
        decode_access_token(str(message.get("token", ""))) if isinstance(message, dict) else None
    )
    if claims is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    channels = [user_channel(claims.user_id)]
    if claims.hub_id and "hub.dashboard.view" in claims.permissions:
        channels.append(hub_channel(claims.hub_id))
    realtime.subscribe(websocket, channels)
    await websocket.send_json({"event": "ready", "data": {"channels": channels}})
    logger.info("[websocket] user=%s subscribed to %s", claims.user_id, channels)

    try:
        while True:
            await websocket.receive_text()
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        realtime.unsubscribe(websocket)
