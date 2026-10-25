"""Shared helpers for API tests: sign-in, raw SQL access, test data builders."""

from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import text

from app.core.db import engine

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
