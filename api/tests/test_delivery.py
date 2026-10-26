"""Driver order flow: scan (BR8), start (BR9), proof of delivery (BR16), failed attempt
with reschedule or return (BR17), manual ETA and giving an order back before pickup (EX4)."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.clock import local_today
from app.modules.delivery.service import release_reschedule
from app.worker.jobs import DISPATCH_RUN, RESCHEDULE_RELEASE
from tests.helpers import (
    assign,
    create_order,
    error_code,
    out_for_delivery,
    run_service,
    scalar,
    upload_photo,
)


async def _status(order_id: object) -> str:
    return str(await scalar("select status from orders where id = :id", id=order_id))


async def _webhooks(waybill: str, event: str) -> int:
    return int(
        await scalar(
            "select count(*) from webhook_deliveries where event_type = :e "
            "and payload->>'waybill_code' = :w",
            e=event,
            w=waybill,
        )
    )


async def test_scan_start_and_deliver_with_proof(client: AsyncClient) -> None:
    order_id = await create_order(client, "DL000001")
    headers = await assign(client, order_id)
    base = f"/api/v1/driver/orders/{order_id}"

    wrong = await client.post(f"{base}/scan", json={"waybill_code": "DL999999"}, headers=headers)
    assert error_code(wrong) == "WAYBILL_MISMATCH"
    early = await client.post(f"{base}/deliver", json={"photo_file_ids": []}, headers=headers)
    assert early.status_code == 409

    scanned = await client.post(f"{base}/scan", json={"waybill_code": "dl000001"}, headers=headers)
    assert scanned.status_code == 200 and scanned.json()["status"] == "PICKED_UP"
    route = (await client.get("/api/v1/driver/route", headers=headers)).json()
    assert route["ready_to_start"] >= 1

    started = await client.post("/api/v1/driver/route/start", headers=headers)
    assert started.status_code == 200 and started.json()["started"] >= 1
    assert await _status(order_id) == "OUT_FOR_DELIVERY"
    assert await scalar("select current_eta is not null from orders where id = :id", id=order_id)

    missing = await client.post(f"{base}/deliver", json={"photo_file_ids": []}, headers=headers)
    assert error_code(missing) == "EVIDENCE_REQUIRED"
    photo = await upload_photo(client, headers)
    delivered = await client.post(
        f"{base}/deliver",
        json={"photo_file_ids": [photo], "note": "Left with guard"},
        headers=headers,
    )
    assert delivered.status_code == 200 and delivered.json()["status"] == "DELIVERED"
    assert await _webhooks("DL000001", "order.delivered") == 1
    proof = await scalar(
        "select payload->>'proof_url' from webhook_deliveries where event_type = 'order.delivered' "
        "and payload->>'waybill_code' = 'DL000001'"
    )
    assert proof == f"/api/v1/files/{photo}"
    image = await client.get(proof)
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"


async def test_failed_attempt_with_date_is_rescheduled_then_released(client: AsyncClient) -> None:
    order_id, headers = await out_for_delivery(client, "DL000002")
    base = f"/api/v1/driver/orders/{order_id}"

    too_far = (local_today() + timedelta(days=30)).isoformat()
    invalid = await client.post(
        f"{base}/fail",
        json={"reason": "CUSTOMER_ABSENT", "proposed_date": too_far},
        headers=headers,
    )
    assert error_code(invalid) == "RESCHEDULE_DATE_INVALID"

    tomorrow = (local_today() + timedelta(days=1)).isoformat()
    failed = await client.post(
        f"{base}/fail",
        json={"reason": "CUSTOMER_ABSENT", "note": "Nobody home", "proposed_date": tomorrow},
        headers=headers,
    )
    assert failed.status_code == 200 and failed.json()["status"] == "RESCHEDULED"
    assert await _webhooks("DL000002", "order.failed") == 1
    job = await scalar(
        "select count(*) from jobs where type = :t and payload->>'order_id' = :o",
        t=RESCHEDULE_RELEASE,
        o=str(order_id),
    )
    assert job == 1

    assert await run_service(release_reschedule, order_id) is True
    assert await _status(order_id) == "AWAITING_ASSIGNMENT"
    assert await scalar("select current_driver_id from orders where id = :id", id=order_id) is None


async def test_failed_attempt_without_date_returns_to_hub(client: AsyncClient) -> None:
    order_id, headers = await out_for_delivery(client, "DL000003")
    failed = await client.post(
        f"/api/v1/driver/orders/{order_id}/fail",
        json={"reason": "CUSTOMER_REFUSED"},
        headers=headers,
    )
    assert failed.json()["status"] == "RETURNING"


async def test_manual_eta_must_be_in_the_future(client: AsyncClient) -> None:
    order_id, headers = await out_for_delivery(client, "DL000004")
    url = f"/api/v1/driver/orders/{order_id}/eta"
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    rejected = await client.put(url, json={"eta": past, "reason": "Traffic"}, headers=headers)
    assert error_code(rejected) == "ETA_IN_PAST"

    later = datetime.now(UTC) + timedelta(hours=3)
    updated = await client.put(
        url, json={"eta": later.isoformat(), "reason": "Heavy rain"}, headers=headers
    )
    assert updated.status_code == 200
    assert await scalar("select eta_source from orders where id = :id", id=order_id) == "MANUAL"
    assert await _webhooks("DL000004", "order.eta_changed") == 1


async def test_driver_gives_order_back_only_before_pickup(client: AsyncClient) -> None:
    order_id = await create_order(client, "DL000005")
    headers = await assign(client, order_id)
    released = await client.post(
        f"/api/v1/driver/orders/{order_id}/release",
        json={"reason": "Vehicle problem"},
        headers=headers,
    )
    assert released.status_code == 204
    assert await _status(order_id) == "AWAITING_ASSIGNMENT"
    queued = await scalar(
        "select count(*) from jobs where type = :t and status = 'PENDING' "
        "and payload->>'order_id' = :o",
        t=DISPATCH_RUN,
        o=str(order_id),
    )
    assert queued == 1

    picked_id, picked_headers = await out_for_delivery(client, "DL000006")
    refused = await client.post(
        f"/api/v1/driver/orders/{picked_id}/release",
        json={"reason": "Vehicle problem"},
        headers=picked_headers,
    )
    assert error_code(refused) == "INVALID_TRANSITION"


async def test_driver_cannot_touch_another_drivers_order(client: AsyncClient) -> None:
    from tests.helpers import DRIVER_2, login

    order_id = await create_order(client, "DL000007")
    await assign(client, order_id)
    other = await login(client, DRIVER_2)
    response = await client.get(f"/api/v1/driver/orders/{order_id}", headers=other)
    assert response.status_code == 404
