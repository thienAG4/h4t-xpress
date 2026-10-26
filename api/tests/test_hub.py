"""Hub manager API (UC-02, H-01, H-03, H-07): dashboard, order board with SLA risk,
order page, drivers, and the manual actions hold, reassign and confirm return."""

from httpx import AsyncClient

from tests.helpers import (
    DRIVER,
    DRIVER_2,
    HUB_MANAGER,
    assign,
    create_order,
    error_code,
    login,
    out_for_delivery,
    pending_offer,
    reset_dispatch,
    scalar,
    sql,
    user_id,
)

BASE = "/api/v1/hub"


async def test_only_hub_managers_see_the_hub(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    for path in ("/dashboard", "/orders", "/drivers"):
        response = await client.get(f"{BASE}{path}", headers=driver)
        assert response.status_code == 403, path


async def test_dashboard_counts_today(client: AsyncClient) -> None:
    manager = await login(client, HUB_MANAGER)
    body = (await client.get(f"{BASE}/dashboard", headers=manager)).json()
    assert body["total"] == sum(body["by_status"].values()) > 0
    assert body["drivers_on_shift"] >= 2
    assert body["on_time_rate_today"] is None or 0 <= body["on_time_rate_today"] <= 1


async def test_risky_orders_come_first_and_can_be_filtered(client: AsyncClient) -> None:
    order_id = await create_order(client, "HB000001")
    await sql(
        "update orders set promised_at = now() - interval '10 minutes' where id = :id", id=order_id
    )
    manager = await login(client, HUB_MANAGER)

    board = (await client.get(f"{BASE}/orders", headers=manager)).json()
    assert board["items"][0]["at_risk"] is True
    risky = (await client.get(f"{BASE}/orders", params={"at_risk": True}, headers=manager)).json()
    assert all(item["at_risk"] for item in risky["items"])
    found = (await client.get(f"{BASE}/orders", params={"q": "hb000001"}, headers=manager)).json()
    assert [item["waybill_code"] for item in found["items"]] == ["HB000001"]
    by_status = (
        await client.get(
            f"{BASE}/orders", params={"status": ["ON_HOLD", "ASSIGNED"]}, headers=manager
        )
    ).json()
    assert {item["status"] for item in by_status["items"]} <= {"ON_HOLD", "ASSIGNED"}

    detail = (await client.get(f"{BASE}/orders/{order_id}", headers=manager)).json()
    assert detail["waybill_code"] == "HB000001"
    assert [event["to_status"] for event in detail["timeline"]] == ["AWAITING_ASSIGNMENT"]
    assert detail["hub_lat"] and detail["items"][0]["qty"] == 2


async def test_orders_of_another_hub_are_hidden(client: AsyncClient) -> None:
    order_id = await create_order(client, "HB000002")
    await sql(
        "update orders set hub_id = (select id from hubs where code <> 'DIAN' limit 1) "
        "where id = :id",
        id=order_id,
    )
    manager = await login(client, HUB_MANAGER)
    response = await client.get(f"{BASE}/orders/{order_id}", headers=manager)
    assert response.status_code == 404


async def test_hold_and_release(client: AsyncClient) -> None:
    order_id = await create_order(client, "HB000003")
    manager = await login(client, HUB_MANAGER)
    held = await client.post(
        f"{BASE}/orders/{order_id}/hold", json={"reason": "Address check"}, headers=manager
    )
    assert held.status_code == 200 and held.json()["status"] == "ON_HOLD"
    twice = await client.post(
        f"{BASE}/orders/{order_id}/hold", json={"reason": "Address check"}, headers=manager
    )
    assert error_code(twice) == "INVALID_TRANSITION"
    released = await client.post(f"{BASE}/orders/{order_id}/release-hold", headers=manager)
    assert released.json()["status"] == "AWAITING_ASSIGNMENT"


async def test_reassign_takes_the_order_back_and_offers_it(client: AsyncClient) -> None:
    order_id = await create_order(client, "HB000004")
    await assign(client, order_id, DRIVER)
    await reset_dispatch({DRIVER: 0.2, DRIVER_2: 1})
    manager = await login(client, HUB_MANAGER)
    d1, d2 = await user_id(DRIVER), await user_id(DRIVER_2)

    candidates = (await client.get(f"{BASE}/orders/{order_id}/candidates", headers=manager)).json()
    assert str(d2) in [c["driver_id"] for c in candidates]
    assert str(d1) not in [c["driver_id"] for c in candidates]

    same = await client.post(
        f"{BASE}/orders/{order_id}/reassign", json={"driver_id": str(d1)}, headers=manager
    )
    assert error_code(same) == "DRIVER_NOT_AVAILABLE"
    moved = await client.post(
        f"{BASE}/orders/{order_id}/reassign", json={"driver_id": str(d2)}, headers=manager
    )
    assert moved.status_code == 200 and moved.json()["status"] == "AWAITING_ASSIGNMENT"
    offer = await pending_offer(order_id)
    assert offer is not None and offer[1] == d2
    assert await scalar("select source from dispatch_offers where id = :id", id=offer[0]) == (
        "MANUAL"
    )

    # Changing the choice withdraws the first offer.
    back = await client.post(
        f"{BASE}/orders/{order_id}/reassign", json={"driver_id": str(d1)}, headers=manager
    )
    assert back.status_code == 200
    offer = await pending_offer(order_id)
    assert offer is not None and offer[1] == d1
    driver2 = await login(client, DRIVER_2)
    assert (await client.get("/api/v1/driver/offers/current", headers=driver2)).json() is None

    drivers = (await client.get(f"{BASE}/drivers", headers=manager)).json()
    row = next(d for d in drivers if d["id"] == str(d1))
    assert row["availability"] == "ONLINE" and row["has_pending_offer"] is True
    route = await client.get(f"{BASE}/drivers/{d1}/route", headers=manager)
    assert route.status_code == 200


async def test_picked_up_parcel_cannot_be_reassigned_directly(client: AsyncClient) -> None:
    order_id, _ = await out_for_delivery(client, "HB000005")
    manager = await login(client, HUB_MANAGER)
    response = await client.post(
        f"{BASE}/orders/{order_id}/reassign",
        json={"driver_id": str(await user_id(DRIVER_2))},
        headers=manager,
    )
    assert error_code(response) == "INVALID_TRANSITION"


async def test_returned_parcel_is_confirmed_at_the_hub(client: AsyncClient) -> None:
    order_id, driver = await out_for_delivery(client, "HB000006")
    await client.post(
        f"/api/v1/driver/orders/{order_id}/fail",
        json={"reason": "WRONG_ADDRESS"},
        headers=driver,
    )
    manager = await login(client, HUB_MANAGER)
    returned = await client.post(f"{BASE}/orders/{order_id}/returned", headers=manager)
    assert returned.status_code == 200 and returned.json()["status"] == "RETURNED_TO_HUB"
    assert returned.json()["attempts"][0]["failure_reason"] == "WRONG_ADDRESS"


async def test_hub_offer_replaces_a_pending_automatic_offer(client: AsyncClient) -> None:
    from app.modules.dispatch.service import run_dispatch
    from app.worker.jobs import DISPATCH_RUN
    from tests.helpers import run_service

    await reset_dispatch({DRIVER_2: 0.5})
    auto_order = await create_order(client, "HB000007")
    assert await run_service(run_dispatch, auto_order) == "offered"
    d2 = await user_id(DRIVER_2)
    manager = await login(client, HUB_MANAGER)

    hub_order = await create_order(client, "HB000008")
    candidates = (await client.get(f"{BASE}/orders/{hub_order}/candidates", headers=manager)).json()
    assert str(d2) in [c["driver_id"] for c in candidates]
    moved = await client.post(
        f"{BASE}/orders/{hub_order}/reassign", json={"driver_id": str(d2)}, headers=manager
    )
    assert moved.status_code == 200, moved.text

    offer = await pending_offer(hub_order)
    assert offer is not None and offer[1] == d2
    assert await pending_offer(auto_order) is None
    requeued = await scalar(
        "select count(*) from jobs where type = :t and status = 'PENDING' "
        "and payload->>'order_id' = :o",
        t=DISPATCH_RUN,
        o=str(auto_order),
    )
    assert requeued == 1

    # A second hub offer to the same driver must wait for the first answer.
    other = await create_order(client, "HB000009")
    busy = await client.post(
        f"{BASE}/orders/{other}/reassign", json={"driver_id": str(d2)}, headers=manager
    )
    assert error_code(busy) == "DRIVER_BUSY"
