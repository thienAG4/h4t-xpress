"""GPS simulator and demo panel (S-04, SPEC §7.2) and the anomaly scan (BR12, EX5, EX6)."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.db import SessionLocal
from app.modules.sim.gps import _advance, gps
from app.modules.tracking.anomaly import scan
from tests.helpers import DRIVER, out_for_delivery, scalar, sql, user_id

SIMULATED_ON_ROAD = """
select count(*) from orders o join users u on u.id = o.current_driver_id
where o.status = 'OUT_FOR_DELIVERY' and u.email not in ('driver1@demo.h4t', 'driver2@demo.h4t')
"""


async def _setting(key: str, value: str) -> None:
    await sql(
        "insert into system_settings (key, value) values (:k, cast(:v as jsonb)) "
        "on conflict (key) do update set value = excluded.value",
        k=key,
        v=value,
    )


def test_advance_walks_along_the_path() -> None:
    path = [(10.0, 106.0), (10.001, 106.0), (10.002, 106.0)]  # about 111 m per segment
    rest = _advance(path, 150)
    assert len(rest) == 2 and 10.0013 < rest[0][0] < 10.0014
    assert _advance(path, 1000) == [(10.002, 106.0)]


async def test_simulated_drivers_move_and_deliver(client: AsyncClient) -> None:
    await _setting("sim.gps_enabled", "true")
    await _setting("sim.speed_factor", "4")
    await _setting("sim.paused_drivers", "{}")
    human_order, _ = await out_for_delivery(client, "SM000001")
    human_before = await sql(
        "select last_lat, last_lng from driver_profiles where user_id = :id",
        id=await user_id(DRIVER),
    )
    on_road = await scalar(SIMULATED_ON_ROAD)
    assert on_road > 0
    locations = await scalar("select count(*) from driver_locations")

    assert await gps.tick() > 0
    assert await scalar("select count(*) from driver_locations") > locations
    human_after = await sql(
        "select last_lat, last_lng from driver_profiles where user_id = :id",
        id=await user_id(DRIVER),
    )
    assert human_after == human_before  # a person drives driver1, the simulator does not

    # Very fast drivers reach their next stop in one tick and deliver (or fail) there.
    await _setting("sim.speed_factor", "100000")
    await gps.tick()
    assert await scalar(SIMULATED_ON_ROAD) < on_road
    proof = await scalar(
        "select count(*) from delivery_attempt_files af join files f on f.id = af.file_id "
        "where f.key = 'sim/proof-of-delivery.jpg'"
    )
    assert proof > 0
    assert await scalar("select status from orders where id = :id", id=human_order) == (
        "OUT_FOR_DELIVERY"
    )

    await _setting("sim.gps_enabled", "false")
    assert await gps.tick() == 0


async def test_demo_panel_lists_and_stops_drivers(client: AsyncClient) -> None:
    from app.seed.runner import run_seed

    await run_seed(reset=True, history_days=2, random_seed=5)  # fresh drivers on the road
    status = (await client.get("/api/v1/sim/demo")).json()
    assert status["gps_enabled"] is True and status["drivers"]
    driver_id = status["drivers"][0]["driver_id"]

    jam = await client.post("/api/v1/sim/demo/traffic-jam", json={"driver_id": driver_id})
    assert jam.status_code == 200
    stuck = next(d for d in jam.json()["drivers"] if d["driver_id"] == driver_id)
    assert stuck["stuck_until"] is not None

    switched = await client.put("/api/v1/sim/demo/gps", json={"enabled": False})
    assert switched.json()["gps_enabled"] is False
    await client.put("/api/v1/sim/demo/gps", json={"enabled": True})

    reset = await client.post("/api/v1/sim/demo/reset")
    assert reset.status_code == 401  # system admin only


async def test_idle_driver_raises_one_incident() -> None:
    await _setting("anomaly.idle_minutes", "3")
    driver_id = await scalar(
        "select o.current_driver_id from orders o join users u on u.id = o.current_driver_id "
        "where o.status = 'OUT_FOR_DELIVERY' and o.active_incident_id is null "
        "and u.email not in ('driver1@demo.h4t', 'driver2@demo.h4t') limit 1"
    )
    assert driver_id is not None
    now = datetime.now(UTC)
    await sql("delete from driver_locations where driver_id = :d", d=driver_id)
    for minutes_ago in (4, 3, 2, 1, 0):
        await sql(
            "insert into driver_locations (driver_id, lat, lng, recorded_at, created_at) "
            "values (:d, 10.9, 106.77, :at, :at)",
            d=driver_id,
            at=now - timedelta(minutes=minutes_ago, seconds=-5),
        )

    async with SessionLocal() as session:
        raised = await scan(session)
    idle = [incident for incident in raised if incident.driver_id == driver_id]
    assert len(idle) == 1 and idle[0].type == "DRIVER_IDLE" and idle[0].source == "SYSTEM"
    held = await scalar(
        "select count(*) from orders where current_driver_id = :d and active_incident_id = :i",
        d=driver_id,
        i=idle[0].id,
    )
    assert held >= 1

    async with SessionLocal() as session:
        again = await scan(session)
    assert all(incident.driver_id != driver_id for incident in again)


async def test_eta_slipping_three_times_raises_eta_anomaly(client: AsyncClient) -> None:
    order_id, _ = await out_for_delivery(client, "SM000002")
    base = datetime.now(UTC) + timedelta(hours=1)
    for step in range(3):
        previous, eta = (
            base + timedelta(minutes=15 * step),
            base + timedelta(minutes=15 * (step + 1)),
        )
        await sql(
            "insert into order_events (id, order_id, type, actor_type, payload, created_at) "
            "values (:id, :o, 'ETA_CHANGED', 'SYSTEM', cast(:p as jsonb), :at)",
            id=uuid.uuid4(),
            o=order_id,
            p=f'{{"eta": "{eta.isoformat()}", "previous": "{previous.isoformat()}"}}',
            at=datetime.now(UTC) - timedelta(minutes=10 - step),
        )
    async with SessionLocal() as session:
        raised = await scan(session)
    anomaly = [incident for incident in raised if incident.type == "ETA_ANOMALY"]
    assert len(anomaly) == 1
    assert (
        await scalar("select active_incident_id from orders where id = :id", id=order_id)
        == anomaly[0].id
    )
