"""Incident flow (UC-03, UC-04): report with evidence, classify (BR13), respond (BR14),
then resolve (BR15) by a new stop order, a replacement driver with hand-over, or a hold."""

import uuid

from httpx import AsyncClient

from app.core.clock import local_today
from app.modules.dispatch.service import run_dispatch
from tests.helpers import (
    DRIVER,
    DRIVER_2,
    HUB_MANAGER,
    error_code,
    login,
    out_for_delivery,
    pending_offer,
    reset_dispatch,
    run_service,
    scalar,
    sql,
    upload_photo,
    user_id,
)

HUB = "/api/v1/hub/incidents"


async def _report(
    client: AsyncClient, headers: dict[str, str], order_ids: list[uuid.UUID], kind: str
) -> dict:
    photo = await upload_photo(client, headers)
    response = await client.post(
        "/api/v1/driver/incidents",
        json={
            "type": kind,
            "description": "Something stopped me on the way to the customer",
            "photo_file_ids": [photo],
            "order_ids": [str(order_id) for order_id in order_ids],
            "lat": 10.91,
            "lng": 106.77,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def _classify_and_respond(
    client: AsyncClient, manager: dict[str, str], incident_id: str, category: str
) -> None:
    classified = await client.post(
        f"{HUB}/{incident_id}/classify",
        json={"category": category, "priority": "HIGH"},
        headers=manager,
    )
    assert classified.status_code == 200, classified.text
    responded = await client.post(
        f"{HUB}/{incident_id}/respond",
        json={"message": "Stay safe, we are handling it."},
        headers=manager,
    )
    assert responded.status_code == 200, responded.text


async def test_report_needs_description_and_evidence(client: AsyncClient) -> None:
    order_id, headers = await out_for_delivery(client, "IN000001")
    no_photo = await client.post(
        "/api/v1/driver/incidents",
        json={
            "type": "WEATHER",
            "description": "Flooded street, cannot pass",
            "photo_file_ids": [],
        },
        headers=headers,
    )
    assert error_code(no_photo) == "EVIDENCE_REQUIRED"
    system_type = await client.post(
        "/api/v1/driver/incidents",
        json={"type": "ETA_ANOMALY", "description": "Flooded street, cannot pass"},
        headers=headers,
    )
    assert system_type.status_code == 422

    incident = await _report(client, headers, [order_id], "WEATHER")
    assert incident["status"] == "OPEN"
    assert incident["suggested_category"] == "OBJECTIVE"
    assert [o["waybill_code"] for o in incident["orders"]] == ["IN000001"]
    assert await scalar("select active_incident_id from orders where id = :id", id=order_id) == (
        uuid.UUID(incident["id"])
    )
    apology = await scalar(
        "select payload->>'message' from webhook_deliveries where event_type = 'order.incident' "
        "and payload->>'waybill_code' = 'IN000001'"
    )
    assert apology.startswith("We are sorry for the delay")

    mine = (await client.get("/api/v1/driver/incidents", headers=headers)).json()
    assert incident["id"] in [item["id"] for item in mine]


async def test_reassign_hands_parcels_over_to_another_driver(client: AsyncClient) -> None:
    order_id, driver1 = await out_for_delivery(client, "IN000002")
    await reset_dispatch({DRIVER: 0.2, DRIVER_2: 1})
    incident = await _report(client, driver1, [order_id], "VEHICLE_BREAKDOWN")
    manager = await login(client, HUB_MANAGER)
    incident_id = incident["id"]
    resolve_url = f"{HUB}/{incident_id}/resolve"
    d1, d2 = await user_id(DRIVER), await user_id(DRIVER_2)
    plan = {"solution": "DRIVER_REASSIGNMENT", "driver_id": str(d2)}

    early = await client.post(resolve_url, json=plan, headers=manager)
    assert error_code(early) == "INCIDENT_NOT_CLASSIFIED"
    await client.post(
        f"{HUB}/{incident_id}/classify",
        json={"category": "SUBJECTIVE", "priority": "HIGH"},
        headers=manager,
    )
    no_answer = await client.post(resolve_url, json=plan, headers=manager)
    assert error_code(no_answer) == "RESPONSE_REQUIRED"
    await client.post(
        f"{HUB}/{incident_id}/respond", json={"message": "Wait for driver 2"}, headers=manager
    )

    candidates = (await client.get(f"{HUB}/{incident_id}/candidates", headers=manager)).json()
    assert str(d2) in [c["driver_id"] for c in candidates]
    assert str(d1) not in [c["driver_id"] for c in candidates]
    direct = await client.post(
        f"/api/v1/hub/orders/{order_id}/reassign", json={"driver_id": str(d2)}, headers=manager
    )
    assert error_code(direct) == "INCIDENT_OPEN"

    # First replacement declines: the incident goes back to review, no automatic dispatch.
    resolving = await client.post(resolve_url, json=plan, headers=manager)
    assert resolving.status_code == 200 and resolving.json()["status"] == "RESOLVING"
    rows = await sql(
        "select status, handover_from_driver_id from orders where id = :id", id=order_id
    )
    assert rows[0][0] == "AWAITING_ASSIGNMENT" and rows[0][1] == d1
    assert await run_service(run_dispatch, order_id) == "incident_open"
    offer = await pending_offer(order_id)
    assert offer is not None and offer[1] == d2
    driver2 = await login(client, DRIVER_2)
    shown = (await client.get("/api/v1/driver/offers/current", headers=driver2)).json()
    assert shown["is_rescue"] is True
    declined = await client.post(
        f"/api/v1/driver/offers/{offer[0]}/decline", json={}, headers=driver2
    )
    assert declined.status_code == 204
    detail = (await client.get(f"{HUB}/{incident_id}", headers=manager)).json()
    assert detail["status"] == "IN_REVIEW"
    assert detail["resolutions"][0]["status"] == "FAILED"
    queued = await scalar(
        "select count(*) from jobs where status = 'PENDING' and payload->>'order_id' = :o",
        o=str(order_id),
    )
    assert queued == 0

    # Second attempt: accepted, driver 2 collects the parcel from driver 1.
    again = await client.post(resolve_url, json=plan, headers=manager)
    assert again.status_code == 200, again.text
    offer = await pending_offer(order_id)
    assert offer is not None
    accepted = await client.post(f"/api/v1/driver/offers/{offer[0]}/accept", headers=driver2)
    assert accepted.status_code == 200
    pickup = [o for o in accepted.json()["to_pick_up"] if o["waybill_code"] == "IN000002"]
    assert pickup and pickup[0]["handover_from"]
    detail = (await client.get(f"{HUB}/{incident_id}", headers=manager)).json()
    assert detail["status"] == "RESOLVED"
    rows = await sql(
        "select status, current_driver_id, active_incident_id from orders where id = :id",
        id=order_id,
    )
    assert rows[0][0] == "ASSIGNED" and rows[0][1] == d2 and rows[0][2] is None
    scanned = await client.post(
        f"/api/v1/driver/orders/{order_id}/scan", json={"waybill_code": "IN000002"}, headers=driver2
    )
    assert scanned.json()["status"] == "PICKED_UP"


async def test_hold_at_hub_takes_parcels_off_the_driver(client: AsyncClient) -> None:
    order_id, driver1 = await out_for_delivery(client, "IN000003")
    incident = await _report(client, driver1, [order_id], "TRAFFIC_ACCIDENT")
    manager = await login(client, HUB_MANAGER)
    await _classify_and_respond(client, manager, incident["id"], "OBJECTIVE")

    resolved = await client.post(
        f"{HUB}/{incident['id']}/resolve",
        json={"solution": "HOLD_AT_HUB", "note": "Bring it back tomorrow"},
        headers=manager,
    )
    assert resolved.status_code == 200 and resolved.json()["status"] == "RESOLVED"
    rows = await sql("select status, current_driver_id from orders where id = :id", id=order_id)
    assert rows[0][0] == "ON_HOLD" and rows[0][1] is None

    released = await client.post(f"/api/v1/hub/orders/{order_id}/release-hold", headers=manager)
    assert released.status_code == 200 and released.json()["status"] == "AWAITING_ASSIGNMENT"


async def test_reroute_changes_the_stop_order(client: AsyncClient) -> None:
    first, driver1 = await out_for_delivery(client, "IN000004", recipient_phone="0123000201")
    second, _ = await out_for_delivery(
        client,
        "IN000005",
        recipient_phone="0123000202",
        delivery_address="2 Truong Chinh, P. Di An, TP.HCM",
        delivery_lat=10.92,
    )
    incident = await _report(client, driver1, [first, second], "TRAFFIC_JAM")
    manager = await login(client, HUB_MANAGER)
    await _classify_and_respond(client, manager, incident["id"], "OBJECTIVE")

    stops = [
        row[0]
        for row in await sql(
            "select s.id from route_stops s join routes r on r.id = s.route_id "
            "where r.driver_id = :d and r.work_date = :day and s.status = 'PENDING' order by s.seq",
            d=await user_id(DRIVER),
            day=local_today(),
        )
    ]
    assert len(stops) >= 2
    wrong = await client.post(
        f"{HUB}/{incident['id']}/resolve",
        json={"solution": "ROUTE_SUGGESTED", "stop_ids": [str(stops[0])]},
        headers=manager,
    )
    assert error_code(wrong) == "STOP_LIST_MISMATCH"

    new_order = list(reversed(stops))
    resolved = await client.post(
        f"{HUB}/{incident['id']}/resolve",
        json={"solution": "ROUTE_SUGGESTED", "stop_ids": [str(s) for s in new_order]},
        headers=manager,
    )
    assert resolved.status_code == 200 and resolved.json()["status"] == "RESOLVED"
    seqs = await sql(
        "select id from route_stops where id = any(:ids) order by seq", ids=list(stops)
    )
    assert [row[0] for row in seqs] == new_order


async def test_hub_summary_and_list(client: AsyncClient) -> None:
    manager = await login(client, HUB_MANAGER)
    summary = (await client.get(f"{HUB}/summary", headers=manager)).json()
    assert set(summary) >= {"open", "in_review", "resolving", "resolved_today", "by_priority"}
    listed = (await client.get(HUB, params={"page_size": 5}, headers=manager)).json()
    assert listed["total"] >= 1 and len(listed["items"]) <= 5

    # Search by code (exact incident) and by period.
    code = listed["items"][0]["code"]
    found = (await client.get(HUB, params={"q": code.lower()}, headers=manager)).json()
    assert [item["code"] for item in found["items"]] == [code]
    nothing = (await client.get(HUB, params={"q": "no-such-incident"}, headers=manager)).json()
    assert nothing["total"] == 0
    recent = (await client.get(HUB, params={"days": 7}, headers=manager)).json()
    every = (await client.get(HUB, params={"page_size": 1}, headers=manager)).json()
    assert recent["total"] <= every["total"]

    driver = await login(client, DRIVER)
    forbidden = await client.get(f"{HUB}/summary", headers=driver)
    assert forbidden.status_code == 403
