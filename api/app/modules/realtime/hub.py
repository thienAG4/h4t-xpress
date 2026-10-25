"""In-process publish/subscribe for WebSocket clients (SPEC §5.5).

One API instance on the free tier, so channels live in memory. With several instances
this class would forward to Redis pub/sub or Postgres LISTEN/NOTIFY instead.

Channels: `user:<id>` (one person) and `hub:<id>` (everyone watching a hub).
"""

import logging
import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def user_channel(user_id: uuid.UUID | str) -> str:
    return f"user:{user_id}"


def hub_channel(hub_id: uuid.UUID | str) -> str:
    return f"hub:{hub_id}"


class RealtimeHub:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)

    def subscribe(self, websocket: WebSocket, channels: list[str]) -> None:
        for channel in channels:
            self._channels[channel].add(websocket)

    def unsubscribe(self, websocket: WebSocket) -> None:
        for sockets in self._channels.values():
            sockets.discard(websocket)

    def subscriber_count(self, channel: str) -> int:
        return len(self._channels.get(channel, ()))

    async def publish(self, channel: str, event: str, data: dict[str, Any]) -> int:
        """Send {event, data} to every socket of the channel; dead sockets are dropped."""
        delivered = 0
        for websocket in list(self._channels.get(channel, ())):
            try:
                await websocket.send_json({"event": event, "data": data})
                delivered += 1
            except Exception:
                self._channels[channel].discard(websocket)
        if delivered:
            logger.debug("[publish] %s %s -> %d sockets", channel, event, delivered)
        return delivered


realtime = RealtimeHub()


async def notify_user(user_id: uuid.UUID | None, event: str, data: dict[str, Any]) -> None:
    if user_id is not None:
        await realtime.publish(user_channel(user_id), event, data)


async def notify_hub(hub_id: uuid.UUID, event: str, data: dict[str, Any]) -> None:
    await realtime.publish(hub_channel(hub_id), event, data)
