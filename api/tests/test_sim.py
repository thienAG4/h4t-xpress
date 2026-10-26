"""ShopNow simulator: order creation through the partner service and webhook receiver."""

import json

from httpx import AsyncClient

from app.core.security import sign_webhook
from tests.helpers import error_code, scalar

SECRET = "shopnow-demo-webhook-secret"


async def test_random_orders_go_through_the_partner_service(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/sim/shopnow/orders/random", json={"hub_code": "LINHXUAN", "count": 3}
    )
    assert created.status_code == 201
    waybills = [order["waybill_code"] for order in created.json()]
    assert len(set(waybills)) == 3
    stored = await scalar(
        "select count(*) from orders o join hubs h on h.id = o.hub_id "
        "where h.code = 'LINHXUAN' and o.waybill_code = any(:codes)",
        codes=waybills,
    )
    assert stored == 3

    listed = (await client.get("/api/v1/sim/shopnow/orders", params={"page_size": 3})).json()
    assert {order["waybill_code"] for order in listed["items"]} == set(waybills)


async def test_manual_order_and_cancel(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/sim/shopnow/orders",
        json={
            "hub_code": "THUDUC",
            "recipient_name": "Khách Hàng Demo",
            "recipient_phone": "0123456789",
            "delivery_address": "48 Võ Văn Ngân, P. Thủ Đức, TP.HCM",
            "items": [{"name": "Balo", "qty": 1}],
            "priority": "EXPRESS",
            "promised_in_hours": 5,
        },
    )
    assert created.status_code == 201
    waybill = created.json()["waybill_code"]
    assert created.json()["priority"] == "EXPRESS"

    cancelled = await client.post(f"/api/v1/sim/shopnow/orders/{waybill}/cancel")
    assert cancelled.json()["last_status"] == "CANCELLED"


async def test_unknown_hub_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/sim/shopnow/orders/random", json={"hub_code": "MARS", "count": 1}
    )
    assert error_code(response) == "HUB_NOT_FOUND"


async def test_webhook_signature_controls_whether_status_is_applied(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/sim/shopnow/orders/random", json={"hub_code": "DIAN", "count": 1}
    )
    waybill = created.json()[0]["waybill_code"]
    body = json.dumps(
        {"event": "order.status_changed", "waybill_code": waybill, "status": "ASSIGNED"}
    ).encode()

    forged = await client.post(
        "/api/v1/sim/shopnow/webhooks", content=body, headers={"X-H4T-Signature": "sha256=bad"}
    )
    assert forged.status_code == 202
    assert forged.json()["signature_valid"] is False
    status = "select last_status from sim_shopnow_orders where waybill_code = :w"
    assert await scalar(status, w=waybill) == "AWAITING_ASSIGNMENT"

    signed = await client.post(
        "/api/v1/sim/shopnow/webhooks",
        content=body,
        headers={"X-H4T-Signature": sign_webhook(body, SECRET)},
    )
    assert signed.json()["signature_valid"] is True
    assert await scalar(status, w=waybill) == "ASSIGNED"

    log = (
        await client.get("/api/v1/sim/shopnow/webhooks", params={"waybill_code": waybill})
    ).json()
    assert log["total"] == 2
