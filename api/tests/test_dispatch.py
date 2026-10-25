"""Dispatch engine: eligibility and ranking (BR4, BR5), sequential offers with timeout
(BR6, BR7), first acceptance wins (BR8), no driver (EX2) and hold after rounds (EX3)."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.modules.dispatch.service import expire_offer, rank_candidates, run_dispatch
from app.modules.settings.service import load_business_settings
from app.worker.jobs import DISPATCH_RUN
from tests.helpers import (
    DRIVER,
    DRIVER_2,
    create_order,
    error_code,
    hub_point,
    login,
    pending_offer,
    reset_dispatch,
    run_service,
    scalar,
    sql,
    user_id,
)

DRIVER_3 = "driver3@demo.h4t"


async def _ranked_ids(exclude: set | None = None) -> list:
    from app.core.db import SessionLocal

    hub_id = await scalar("select id from hubs where code = 'DIAN'")
    async with SessionLocal() as session:
        settings = await load_business_settings(session)
        ranked = await rank_candidates(
            session, settings, hub_id=hub_id, origin=await hub_point(), exclude=exclude
        )
    return [candidate.driver_id for candidate in ranked]


async def test_only_eligible_drivers_are_ranked_nearest_first() -> None:
    await reset_dispatch({DRIVER: 0.2, DRIVER_2: 12})
    d1, d2, d3 = await user_id(DRIVER), await user_id(DRIVER_2), await user_id(DRIVER_3)

    ranked = await _ranked_ids()
    assert ranked[:2] == [d1, d2]
    assert d3 not in ranked  # offline
    assert await _ranked_ids(exclude={d1}) == [d2]

    # An app that stopped sending heartbeats is not offered work.
    await sql(
        "update driver_profiles set last_seen_at = now() - interval '2 days' where user_id = :id",
        id=d2,
    )
    assert await _ranked_ids() == [d1]


async def test_unanswered_offer_moves_to_next_driver_then_first_accept_wins(
    client: AsyncClient,
) -> None:
    await reset_dispatch({DRIVER: 0.2, DRIVER_2: 12})
    order_id = await create_order(client, "DP000001")
    d1, d2 = await user_id(DRIVER), await user_id(DRIVER_2)

    assert await run_service(run_dispatch, order_id) == "offered"
    first = await pending_offer(order_id)
    assert first is not None and first[1] == d1
    driver1 = await login(client, DRIVER)
    current = (await client.get("/api/v1/driver/offers/current", headers=driver1)).json()
    assert current["id"] == str(first[0])
    assert current["waybill_codes"] == ["DP000001"]
    assert 0 < current["seconds_left"] <= 30
    assert await run_service(run_dispatch, order_id) == "waiting_for_answer"

    # BR7: the timeout passes without an answer.
    await sql(
        "update dispatch_offers set expires_at = :at where id = :id",
        at=datetime.now(UTC) - timedelta(seconds=5),
        id=first[0],
    )
    assert await run_service(expire_offer, first[0]) is True
    assert (await client.get("/api/v1/driver/offers/current", headers=driver1)).json() is None
    late = await client.post(f"/api/v1/driver/offers/{first[0]}/accept", headers=driver1)
    assert late.status_code == 409 and error_code(late) == "OFFER_CLOSED"

    assert await run_service(run_dispatch, order_id) == "offered"
    second = await pending_offer(order_id)
    assert second is not None and second[1] == d2
    assert await scalar("select rank from dispatch_offers where id = :id", id=second[0]) == 2

    driver2 = await login(client, DRIVER_2)
    accepted = await client.post(f"/api/v1/driver/offers/{second[0]}/accept", headers=driver2)
    assert accepted.status_code == 200
    assert "DP000001" in [o["waybill_code"] for o in accepted.json()["to_pick_up"]]
    rows = await sql(
        "select status, current_driver_id, route_stop_id from orders where id = :id", id=order_id
    )
    assert rows[0][0] == "ASSIGNED" and rows[0][1] == d2 and rows[0][2] is not None
    assert (
        await scalar(
            "select count(*) from webhook_deliveries where event_type = 'order.driver_assigned' "
            "and payload->>'waybill_code' = 'DP000001'"
        )
        == 1
    )
    again = await client.post(f"/api/v1/driver/offers/{second[0]}/accept", headers=driver2)
    assert again.status_code == 409


async def test_order_goes_on_hold_after_every_round_is_declined(client: AsyncClient) -> None:
    await reset_dispatch({DRIVER: 0.2, DRIVER_2: 12})
    order_id = await create_order(client, "DP000002")
    headers = {DRIVER: await login(client, DRIVER), DRIVER_2: await login(client, DRIVER_2)}
    emails = {await user_id(DRIVER): DRIVER, await user_id(DRIVER_2): DRIVER_2}
    max_rounds = 3

    for round_no in range(1, max_rounds + 1):
        for _ in range(2):  # two eligible drivers per round
            assert await run_service(run_dispatch, order_id) == "offered"
            offer = await pending_offer(order_id)
            assert offer is not None
            declined = await client.post(
                f"/api/v1/driver/offers/{offer[0]}/decline",
                json={"reason": "Too far"},
                headers=headers[emails[offer[1]]],
            )
            assert declined.status_code == 204
        if round_no < max_rounds:
            # The next round waits for the retry delay, then starts again.
            assert await run_service(run_dispatch, order_id) == "next_round_scheduled"
            await sql(
                "update dispatch_offers set responded_at = responded_at - interval '10 minutes' "
                "where order_id = :id",
                id=order_id,
            )

    assert await run_service(run_dispatch, order_id) == "on_hold"
    assert await scalar("select status from orders where id = :id", id=order_id) == "ON_HOLD"
    assert (
        await scalar("select max(round) from dispatch_offers where order_id = :id", id=order_id)
        == 3
    )
    assert (
        await scalar(
            "select count(*) from webhook_deliveries where event_type = 'order.status_changed' "
            "and payload->>'waybill_code' = 'DP000002' and payload->>'status' = 'ON_HOLD'"
        )
        == 1
    )


async def test_no_driver_available_retries_later(client: AsyncClient) -> None:
    await reset_dispatch({})
    order_id = await create_order(client, "DP000003")
    assert await run_service(run_dispatch, order_id) == "no_driver"
    retry = await scalar(
        "select run_at from jobs where type = :t "
        "and status = 'PENDING' and payload->>'order_id' = :o",
        t=DISPATCH_RUN,
        o=str(order_id),
    )
    assert retry > datetime.now(UTC) + timedelta(seconds=30)
    assert await scalar("select status from orders where id = :id", id=order_id) == (
        "AWAITING_ASSIGNMENT"
    )
