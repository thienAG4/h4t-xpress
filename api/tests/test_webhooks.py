"""Partner webhooks (SPEC §3.7): signed delivery to the ShopNow receiver, retry with
backoff, and the customer tracking page built only from received webhooks (S-03)."""

import uuid

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.partner.webhooks import deliver_pending_webhooks
from tests.helpers import (
    DRIVER,
    assign,
    error_code,
    out_for_delivery,
    scalar,
    sql,
    upload_photo,
)


async def _only_pending(waybill: str) -> None:
    """Older test data must not take the delivery slots of this test."""
    await sql(
        "update webhook_deliveries set status = 'SENT' where status = 'PENDING' "
        "and coalesce(payload->>'waybill_code', '') <> :w",
        w=waybill,
    )


async def _deliver_to_shopnow() -> int:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as http:
        return await deliver_pending_webhooks(client=http)


async def _sim_order(client: AsyncClient) -> str:
    created = await client.post(
        "/api/v1/sim/shopnow/orders",
        json={
            "hub_code": "DIAN",
            "recipient_name": "Tran Thi Mai",
            "recipient_phone": "0909000111",
            "delivery_address": "20 Nguyen An Ninh, Di An",
            "delivery_lat": 10.905,
            "delivery_lng": 106.771,
            "items": [{"name": "Shoes", "qty": 1}],
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["waybill_code"])


async def test_webhooks_reach_shopnow_and_feed_the_tracking_page(client: AsyncClient) -> None:
    waybill = await _sim_order(client)
    order_id = uuid.UUID(
        str(await scalar("select id from orders where waybill_code = :w", w=waybill))
    )
    await assign(client, order_id, DRIVER)
    await _only_pending(waybill)

    assert await _deliver_to_shopnow() >= 1
    statuses = await sql(
        "select status, attempts from webhook_deliveries where payload->>'waybill_code' = :w",
        w=waybill,
    )
    assert statuses and all(row[0] == "SENT" and row[1] == 1 for row in statuses)
    valid = await scalar(
        "select bool_and(signature_valid) from sim_shopnow_webhooks where waybill_code = :w",
        w=waybill,
    )
    assert valid is True

    page = (await client.get(f"/api/v1/sim/track/{waybill.lower()}")).json()
    assert page["status"] == "ASSIGNED"
    assert page["recipient_name"] == "T. T. Mai"
    assert page["driver"]["name"]
    assert page["steps"][0]["title"].startswith("Driver assigned")
    assert page["steps"][-1]["title"] == "Order received"


async def test_tracking_page_shows_delay_apology_then_delivery(client: AsyncClient) -> None:
    waybill = await _sim_order(client)
    order_id = uuid.UUID(
        str(await scalar("select id from orders where waybill_code = :w", w=waybill))
    )
    headers = await assign(client, order_id, DRIVER)
    await client.post(
        f"/api/v1/driver/orders/{order_id}/scan", json={"waybill_code": waybill}, headers=headers
    )
    await client.post("/api/v1/driver/route/start", headers=headers)
    photo = await upload_photo(client, headers)
    reported = await client.post(
        "/api/v1/driver/incidents",
        json={
            "type": "TRAFFIC_JAM",
            "description": "Stuck in traffic near the market",
            "photo_file_ids": [photo],
            "order_ids": [str(order_id)],
        },
        headers=headers,
    )
    assert reported.status_code == 201
    await _only_pending(waybill)
    await _deliver_to_shopnow()

    page = (await client.get(f"/api/v1/sim/track/{waybill}")).json()
    assert page["status"] == "OUT_FOR_DELIVERY"
    assert page["delay_message"].startswith("We are sorry for the delay")
    assert page["steps"][0]["title"] == "Delay on the way"

    proof = await upload_photo(client, headers)
    await client.post(
        f"/api/v1/driver/orders/{order_id}/deliver",
        json={"photo_file_ids": [proof]},
        headers=headers,
    )
    await _only_pending(waybill)
    await _deliver_to_shopnow()
    page = (await client.get(f"/api/v1/sim/track/{waybill}")).json()
    assert page["status"] == "DELIVERED" and page["status_label"] == "Delivered"
    assert page["delay_message"] is None
    assert page["proof_url"] == f"/api/v1/files/{proof}"


async def test_failed_delivery_is_retried_with_backoff_then_given_up(client: AsyncClient) -> None:
    order_id, _ = await out_for_delivery(client, "WH000001")
    await _only_pending("WH000001")
    broken = httpx.MockTransport(lambda request: httpx.Response(500))

    async with AsyncClient(transport=broken) as http:
        assert await deliver_pending_webhooks(client=http) >= 1
    rows = await sql(
        "select status, attempts, last_error, next_attempt_at > now() + interval '50 seconds' "
        "from webhook_deliveries where payload->>'waybill_code' = 'WH000001'"
    )
    assert all(
        row[0] == "PENDING" and row[1] == 1 and row[2] == "HTTP 500" and row[3] for row in rows
    )

    # The last allowed attempt fails too: the delivery is marked FAILED for the ops log.
    await sql(
        "update webhook_deliveries set attempts = 5, next_attempt_at = now() "
        "where payload->>'waybill_code' = 'WH000001'"
    )
    async with AsyncClient(transport=broken) as http:
        await deliver_pending_webhooks(client=http)
    statuses = await sql(
        "select distinct status from webhook_deliveries where payload->>'waybill_code' = 'WH000001'"
    )
    assert [row[0] for row in statuses] == ["FAILED"]
    assert order_id


async def test_forged_webhook_is_stored_but_ignored(client: AsyncClient) -> None:
    waybill = await _sim_order(client)
    forged = await client.post(
        "/api/v1/sim/shopnow/webhooks",
        json={"event": "order.delivered", "waybill_code": waybill, "status": "DELIVERED"},
        headers={"X-H4T-Signature": "sha256=forged"},
    )
    assert forged.status_code == 202 and forged.json()["signature_valid"] is False
    page = (await client.get(f"/api/v1/sim/track/{waybill}")).json()
    assert page["status"] == "AWAITING_ASSIGNMENT"
    assert len(page["steps"]) == 1


async def test_unknown_waybill_is_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/sim/track/NOPE0000")
    assert response.status_code == 404 and error_code(response) == "ORDER_NOT_FOUND"
