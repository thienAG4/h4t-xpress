"""Road routing (SPEC §3.3, §5.7) and route planning (H-02, UC-03): OSRM client with
fallback, ETA from road durations, optimise preview and saving a new stop order."""

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.modules.routing.osrm import decode_polyline, osrm
from app.modules.routing.planning import nearest_neighbour
from tests.helpers import (
    DRIVER,
    HUB_MANAGER,
    error_code,
    login,
    out_for_delivery,
    scalar,
    sql,
    user_id,
)

# Google's reference example for the encoded polyline format.
SAMPLE_POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def _fake_osrm(request: httpx.Request) -> httpx.Response:
    """Every leg takes 10 minutes and 3 km; trips visit the points in reverse order."""
    path = request.url.path
    count = len(path.rsplit("/", 1)[-1].split(";"))
    legs = [{"duration": 600.0, "distance": 3000.0} for _ in range(count - 1)]
    body: dict[str, Any] = {"code": "Ok"}
    route = {
        "legs": legs,
        "duration": 600.0 * len(legs),
        "distance": 3000.0 * len(legs),
        "geometry": SAMPLE_POLYLINE,
    }
    if "/trip/" in path:
        order = [0, *reversed(range(1, count))]
        body["trips"] = [{**route, "duration": 300.0 * len(legs)}]
        body["waypoints"] = [{"waypoint_index": order.index(i)} for i in range(count)]
    else:
        body["routes"] = [route]
    return httpx.Response(200, json=body)


@pytest.fixture
def road_server() -> Iterator[None]:
    settings = get_settings()
    settings.osrm_enabled = True
    osrm.use_client(httpx.AsyncClient(transport=httpx.MockTransport(_fake_osrm)))
    yield
    settings.osrm_enabled = False
    osrm.use_client(None)


def test_polyline_decoding_matches_the_reference() -> None:
    assert decode_polyline(SAMPLE_POLYLINE) == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_nearest_neighbour_visits_closest_first() -> None:
    start = (10.90, 106.77)
    points = [(10.95, 106.77), (10.91, 106.77), (10.93, 106.77)]
    assert nearest_neighbour(start, points) == [1, 2, 0]


async def test_route_and_trip_use_the_server(road_server: None) -> None:
    road = await osrm.route([(10.9, 106.7), (10.8, 106.7), (10.7, 106.7)])
    assert road is not None and road.leg_durations_s == [600.0, 600.0]
    trip = await osrm.trip([(10.9, 106.7), (10.8, 106.7), (10.7, 106.7), (10.6, 106.7)])
    assert trip is not None and trip.order == [0, 3, 2, 1]


async def test_failure_returns_nothing_and_cools_down() -> None:
    calls = 0

    def broken(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("too slow")

    settings = get_settings()
    settings.osrm_enabled = True
    osrm.use_client(httpx.AsyncClient(transport=httpx.MockTransport(broken)))
    try:
        assert await osrm.route([(10.9, 106.7), (10.8, 106.7)]) is None
        assert await osrm.route([(10.9, 106.7), (10.7, 106.7)]) is None
        assert calls == 1  # the second call is skipped during the cool-down
    finally:
        settings.osrm_enabled = False
        osrm.use_client(None)


async def test_eta_uses_road_durations_when_available(
    client: AsyncClient, road_server: None
) -> None:
    order_id, _ = await out_for_delivery(client, "RT000001")
    rows = await sql(
        "select o.eta_degraded, r.polyline from orders o "
        "join route_stops s on s.id = o.route_stop_id "
        "join routes r on r.id = s.route_id where o.id = :id",
        id=order_id,
    )
    assert rows[0][0] is False
    assert rows[0][1] == SAMPLE_POLYLINE


async def test_eta_falls_back_to_an_estimate_without_osrm(client: AsyncClient) -> None:
    order_id, headers = await out_for_delivery(client, "RT000002")
    assert await scalar("select eta_degraded from orders where id = :id", id=order_id) is True
    route = (await client.get("/api/v1/driver/route", headers=headers)).json()
    assert route["route_id"] and route["geometry"] is None


async def test_hub_plans_and_reorders_a_route(client: AsyncClient) -> None:
    first, _ = await out_for_delivery(client, "RT000003", recipient_phone="0123000301")
    await out_for_delivery(
        client,
        "RT000004",
        recipient_phone="0123000302",
        delivery_address="9 Truong Chinh, P. Di An, TP.HCM",
        delivery_lat=10.93,
    )
    manager = await login(client, HUB_MANAGER)
    d1 = await user_id(DRIVER)

    routes = (await client.get("/api/v1/hub/routes", headers=manager)).json()
    mine = next(route for route in routes if route["driver_id"] == str(d1))
    assert mine["orders_active"] >= 2 and mine["stops_pending"] >= 2

    detail = (await client.get(f"/api/v1/hub/routes/{mine['id']}", headers=manager)).json()
    pending = [stop["id"] for stop in detail["stops"] if stop["status"] == "PENDING"]
    assert detail["eta_is_estimate"] is True and len(pending) >= 2

    preview = await client.post(f"/api/v1/hub/routes/{mine['id']}/optimize", headers=manager)
    assert preview.status_code == 200
    body = preview.json()
    assert body["method"] == "nearest_neighbor"
    assert sorted(body["suggested_stop_ids"]) == sorted(pending)

    wrong = await client.put(
        f"/api/v1/hub/routes/{mine['id']}/stops/order",
        json={"stop_ids": pending[:1]},
        headers=manager,
    )
    assert error_code(wrong) == "STOP_LIST_MISMATCH"
    reversed_ids = list(reversed(pending))
    saved = await client.put(
        f"/api/v1/hub/routes/{mine['id']}/stops/order",
        json={"stop_ids": reversed_ids},
        headers=manager,
    )
    assert saved.status_code == 200
    order = [s["id"] for s in saved.json()["stops"] if s["status"] == "PENDING"]
    assert order == reversed_ids
    assert first

    driver = await login(client, DRIVER)
    forbidden = await client.get("/api/v1/hub/routes", headers=driver)
    assert forbidden.status_code == 403
