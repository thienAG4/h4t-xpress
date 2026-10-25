"""Inbound partner API: authentication, validation (BR2), idempotency and cancellation."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.helpers import SHOPNOW_KEY, error_code, partner_order, scalar, sql

KEY = {"X-API-Key": SHOPNOW_KEY}


async def test_api_key_is_required(client: AsyncClient) -> None:
    missing = await client.post("/api/v1/partner/v1/orders", json=partner_order("PT000001"))
    wrong = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order("PT000001"), headers={"X-API-Key": "x"}
    )
    assert missing.status_code == wrong.status_code == 401
    assert error_code(missing) == "API_KEY_MISSING"
    assert error_code(wrong) == "API_KEY_INVALID"


async def test_create_order_then_reject_duplicate(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order("PT000002"), headers=KEY
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "AWAITING_ASSIGNMENT"
    assert body["hub_code"] == "DIAN"
    assert [event["to_status"] for event in body["timeline"]] == ["AWAITING_ASSIGNMENT"]
    area = await scalar(
        "select a.code from orders o join areas a on a.id = o.delivery_area_id "
        "where o.waybill_code = 'PT000002'"
    )
    assert area == "DI_AN"

    duplicate = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order("PT000002"), headers=KEY
    )
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "DUPLICATE_WAYBILL"


async def test_invalid_payload_lists_the_wrong_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/partner/v1/orders",
        json=partner_order("PT000003", items=[], recipient_phone="12345"),
        headers=KEY,
    )
    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert fields == {"items", "recipient_phone"}


async def test_business_rules_on_hub_and_promise(client: AsyncClient) -> None:
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    in_past = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order("PT000004", promised_at=past), headers=KEY
    )
    unknown_hub = await client.post(
        "/api/v1/partner/v1/orders", json=partner_order("PT000005", hub_code="NOPE"), headers=KEY
    )
    assert error_code(in_past) == "PROMISE_IN_PAST"
    assert error_code(unknown_hub) == "HUB_NOT_FOUND"


async def test_cancel_queues_a_webhook_and_is_final(client: AsyncClient) -> None:
    await client.post("/api/v1/partner/v1/orders", json=partner_order("PT000006"), headers=KEY)
    cancelled = await client.post(
        "/api/v1/partner/v1/orders/PT000006/cancel",
        json={"reason": "Buyer changed mind"},
        headers=KEY,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    queued = await scalar(
        "select count(*) from webhook_deliveries "
        "where payload->>'waybill_code' = 'PT000006' and status = 'PENDING'"
    )
    assert queued == 1

    again = await client.post("/api/v1/partner/v1/orders/PT000006/cancel", headers=KEY)
    assert again.status_code == 409
    assert error_code(again) == "CANCEL_NOT_ALLOWED"


async def test_cannot_cancel_after_pickup(client: AsyncClient) -> None:
    await client.post("/api/v1/partner/v1/orders", json=partner_order("PT000007"), headers=KEY)
    await sql("update orders set status = 'PICKED_UP' where waybill_code = 'PT000007'")
    response = await client.post("/api/v1/partner/v1/orders/PT000007/cancel", headers=KEY)
    assert error_code(response) == "CANCEL_NOT_ALLOWED"


async def test_unknown_waybill_is_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/partner/v1/orders/NOPE0001", headers=KEY)
    assert response.status_code == 404
