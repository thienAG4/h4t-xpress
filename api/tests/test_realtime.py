"""Realtime channels (SPEC §5.5): in-process pub/sub and the WebSocket handshake."""

import warnings
from typing import Any

import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import app
from app.modules.realtime.hub import RealtimeHub
from tests.helpers import HUB_MANAGER, sql

with warnings.catch_warnings():
    # Starlette now suggests httpx2 for its TestClient; only this file needs it (WebSocket).
    warnings.simplefilter("ignore")
    from starlette.testclient import TestClient


class FakeSocket:
    def __init__(self, *, broken: bool = False) -> None:
        self.sent: list[dict[str, Any]] = []
        self.broken = broken

    async def send_json(self, data: dict[str, Any]) -> None:
        if self.broken:
            raise RuntimeError("connection closed")
        self.sent.append(data)


async def test_publish_reaches_subscribers_and_drops_dead_sockets() -> None:
    hub = RealtimeHub()
    alive, dead, other = FakeSocket(), FakeSocket(broken=True), FakeSocket()
    hub.subscribe(alive, ["hub:1"])  # type: ignore[arg-type]
    hub.subscribe(dead, ["hub:1"])  # type: ignore[arg-type]
    hub.subscribe(other, ["user:2"])  # type: ignore[arg-type]

    assert await hub.publish("hub:1", "order.updated", {"order_id": "x"}) == 1
    assert alive.sent == [{"event": "order.updated", "data": {"order_id": "x"}}]
    assert other.sent == []
    assert hub.subscriber_count("hub:1") == 1


async def test_websocket_requires_a_valid_token_first() -> None:
    rows = await sql("select u.id, u.hub_id from users u where u.email = :e", e=HUB_MANAGER)
    user_id, hub_id = rows[0]
    token, _ = create_access_token(
        user_id=user_id, role="HUB_MANAGER", hub_id=hub_id, permissions=["hub.dashboard.view"]
    )
    http = TestClient(app)  # no lifespan: the worker and engine stay untouched
    with http.websocket_connect("/ws") as socket:
        socket.send_json({"type": "auth", "token": token})
        ready = socket.receive_json()
        assert ready["event"] == "ready"
        assert ready["data"]["channels"] == [f"user:{user_id}", f"hub:{hub_id}"]
        socket.send_text("ping")
        assert socket.receive_text() == "pong"

    with http.websocket_connect("/ws") as socket:
        socket.send_json({"type": "auth", "token": "not-a-token"})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1008
