"""Shared helpers for API tests: sign-in, raw SQL access, test data builders."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import text

from app.core.db import SessionLocal, engine

DEMO_PASSWORD = "Demo@12345"
DRIVER = "driver1@demo.h4t"
HUB_MANAGER = "hub.dian@demo.h4t"
EXECUTIVE = "exec@demo.h4t"
ADMIN = "admin@demo.h4t"
SHOPNOW_KEY = "shopnow-demo-key"


async def login(
    client: AsyncClient, identifier: str, password: str = DEMO_PASSWORD
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"identifier": identifier, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def error_code(response: Response) -> str:
    return str(response.json()["error"]["code"])


async def sql(statement: str, **params: Any) -> list[Any]:
    """Run raw SQL in its own transaction; returns rows for SELECT statements."""
    async with engine.begin() as conn:
        result = await conn.execute(text(statement), params)
        return list(result) if result.returns_rows else []


async def scalar(statement: str, **params: Any) -> Any:
    rows = await sql(statement, **params)
    return rows[0][0] if rows else None


def partner_order(waybill: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "waybill_code": waybill,
        "partner_order_ref": f"REF-{waybill}",
        "hub_code": "DIAN",
        "recipient_name": "Nguyễn Văn Test",
        "recipient_phone": "0123000111",
        "delivery_address": "15 Nguyễn An Ninh, P. Dĩ An, TP.HCM",
        "delivery_lat": 10.906,
        "delivery_lng": 106.770,
        "weight_kg": "1.5",
        "length_cm": "20",
        "width_cm": "15",
        "height_cm": "10",
        "cod_amount": "250000",
        "items": [{"name": "Sách", "qty": 2}],
        "priority": "NORMAL",
        "promised_at": (datetime.now(UTC) + timedelta(hours=8)).isoformat(),
    }
    body.update(overrides)
    return body


# =============================== Phase 2: dispatch and delivery ===============================

DRIVER_2 = "driver2@demo.h4t"
PARTNER_KEY = {"X-API-Key": SHOPNOW_KEY}
# 1x1 transparent PNG, enough for the upload endpoint.
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


async def user_id(email: str) -> uuid.UUID:
    return uuid.UUID(str(await scalar("select id from users where email = :e", e=email)))


async def hub_point(code: str = "DIAN") -> tuple[float, float]:
    rows = await sql("select lat, lng from hubs where code = :c", c=code)
    return float(rows[0][0]), float(rows[0][1])


async def create_order(client: AsyncClient, waybill: str, **overrides: Any) -> uuid.UUID:
    response = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order(waybill, **overrides), headers=PARTNER_KEY
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(str(await scalar("select id from orders where waybill_code = :w", w=waybill)))


async def reset_dispatch(online: dict[str, float] | None = None) -> None:
    """Quiet the dispatch world: no open offers, no queued jobs, every DIAN driver offline.

    `online` maps driver e-mails to their distance from the hub in km (north of it).
    """
    await sql("update dispatch_offers set status = 'CANCELLED' where status = 'PENDING'")
    await sql("update jobs set status = 'DONE' where status in ('PENDING', 'RUNNING')")
    await sql(
        "update driver_profiles set availability = 'OFFLINE' where user_id in "
        "(select u.id from users u join hubs h on h.id = u.hub_id where h.code = 'DIAN')"
    )
    lat, lng = await hub_point()
    for email, km in (online or {}).items():
        await sql(
            "update driver_profiles set availability = 'ONLINE', last_seen_at = now(), "
            "last_lat = :lat, last_lng = :lng where user_id = :id",
            lat=lat + km / 111.0,
            lng=lng,
            id=await user_id(email),
        )


async def run_service[T](fn: Callable[..., Awaitable[T]], *args: Any) -> T:
    """Call a service function (job handler) with its own session, like the worker does."""
    async with SessionLocal() as session:
        return await fn(session, *args)


async def pending_offer(order_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID] | None:
    """(offer id, driver id) of the open offer covering the order."""
    rows = await sql(
        "select id, driver_id from dispatch_offers where status = 'PENDING' and "
        "(order_id = :o or bundle_order_ids @> jsonb_build_array(cast(:o as text)))",
        o=order_id,
    )
    return (rows[0][0], rows[0][1]) if rows else None


async def assign(client: AsyncClient, order_id: uuid.UUID, email: str = DRIVER) -> dict[str, str]:
    """Give the order to one driver through the real dispatch path; returns their headers."""
    from app.modules.dispatch.service import run_dispatch

    await reset_dispatch({email: 0.5})
    assert await run_service(run_dispatch, order_id) == "offered"
    offer = await pending_offer(order_id)
    assert offer is not None
    headers = await login(client, email)
    accepted = await client.post(f"/api/v1/driver/offers/{offer[0]}/accept", headers=headers)
    assert accepted.status_code == 200, accepted.text
    return headers


async def upload_photo(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        "/api/v1/files", files={"file": ("proof.png", PNG_1PX, "image/png")}, headers=headers
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def out_for_delivery(
    client: AsyncClient, waybill: str, email: str = DRIVER, **overrides: Any
) -> tuple[uuid.UUID, dict[str, str]]:
    """New order, assigned to `email`, scanned and on the road."""
    order_id = await create_order(client, waybill, **overrides)
    headers = await assign(client, order_id, email)
    scanned = await client.post(
        f"/api/v1/driver/orders/{order_id}/scan", json={"waybill_code": waybill}, headers=headers
    )
    assert scanned.status_code == 200, scanned.text
    started = await client.post("/api/v1/driver/route/start", headers=headers)
    assert started.status_code == 200, started.text
    return order_id, headers
