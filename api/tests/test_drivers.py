"""Driver home, shift registration rules (UC-01) and availability (FR-D-02)."""

from datetime import timedelta

from httpx import AsyncClient, Response

from app.core.clock import local_today
from tests.helpers import DRIVER, HUB_MANAGER, error_code, login, scalar, sql


async def _slots(client: AsyncClient, headers: dict[str, str], offset: int) -> dict[str, dict]:
    day = local_today() + timedelta(days=offset)
    days = (
        await client.get(
            "/api/v1/driver/shifts",
            params={"date_from": day.isoformat(), "days": 1},
            headers=headers,
        )
    ).json()
    return {slot["code"]: slot for slot in days[0]["slots"]}


async def _register(
    client: AsyncClient, headers: dict[str, str], shift_id: str, offset: int
) -> Response:
    day = local_today() + timedelta(days=offset)
    return await client.post(
        "/api/v1/driver/shift-registrations",
        json={"shift_id": shift_id, "work_date": day.isoformat()},
        headers=headers,
    )


async def test_driver_home_shows_hub_and_availability(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    today = (await client.get("/api/v1/driver/today", headers=driver)).json()
    assert today["hub"]["code"] == "DIAN"
    assert today["availability"] == "OFFLINE"
    assert today["date"] == local_today().isoformat()


async def test_shift_list_has_three_slots_per_day(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    days = (await client.get("/api/v1/driver/shifts", headers=driver)).json()
    assert len(days) == 7
    assert all(len(day["slots"]) == 3 for day in days)


async def test_register_overlap_and_cancel(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    slots = await _slots(client, driver, offset=4)
    assert slots["MORNING"]["status"] == "AVAILABLE"

    morning = await _register(client, driver, slots["MORNING"]["shift_id"], offset=4)
    assert morning.status_code == 201
    again = await _register(client, driver, slots["MORNING"]["shift_id"], offset=4)
    assert error_code(again) == "ALREADY_REGISTERED"
    overlap = await _register(client, driver, slots["FULL_DAY"]["shift_id"], offset=4)
    assert error_code(overlap) == "SHIFT_OVERLAP"
    afternoon = await _register(client, driver, slots["AFTERNOON"]["shift_id"], offset=4)
    assert afternoon.status_code == 201

    after = await _slots(client, driver, offset=4)
    assert after["MORNING"]["status"] == "REGISTERED"
    assert after["FULL_DAY"]["status"] == "CONFLICT"

    registration_id = morning.json()["id"]
    cancelled = await client.delete(
        f"/api/v1/driver/shift-registrations/{registration_id}", headers=driver
    )
    assert cancelled.status_code == 204
    gone = await client.delete(
        f"/api/v1/driver/shift-registrations/{registration_id}", headers=driver
    )
    assert error_code(gone) == "REGISTRATION_NOT_FOUND"

    # A cancelled registration can be taken again.
    assert (
        await _register(client, driver, slots["MORNING"]["shift_id"], offset=4)
    ).status_code == 201


async def test_full_shift_and_closed_dates_are_rejected(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    slots = await _slots(client, driver, offset=5)
    shift_id = slots["FULL_DAY"]["shift_id"]
    day = local_today() + timedelta(days=5)
    other_driver = await scalar("select id from users where email = 'driver2@demo.h4t'")
    await sql("update shifts set capacity = 1 where id = :id", id=shift_id)
    await sql(
        "insert into shift_registrations (id, driver_id, shift_id, work_date, status) "
        "values (gen_random_uuid(), :driver, :shift, :day, 'REGISTERED')",
        driver=other_driver,
        shift=shift_id,
        day=day,
    )
    try:
        full = await _register(client, driver, shift_id, offset=5)
        assert error_code(full) == "SHIFT_FULL"
    finally:
        await sql("update shifts set capacity = 8 where id = :id", id=shift_id)

    too_far = await _register(client, driver, shift_id, offset=30)
    past = await _register(client, driver, shift_id, offset=-1)
    assert error_code(too_far) == error_code(past) == "SHIFT_CLOSED"


async def test_going_online_needs_a_shift_today(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    driver_id = await scalar("select id from users where email = :e", e=DRIVER)
    await sql(
        "delete from shift_registrations where driver_id = :d and work_date = :day",
        d=driver_id,
        day=local_today(),
    )
    denied = await client.put("/api/v1/driver/availability", json={"online": True}, headers=driver)
    assert error_code(denied) == "NO_SHIFT_TODAY"

    shift_id = await scalar(
        "select s.id from shifts s join users u on u.hub_id = s.hub_id "
        "where u.id = :d and s.code = 'FULL_DAY'",
        d=driver_id,
    )
    await sql(
        "insert into shift_registrations (id, driver_id, shift_id, work_date, status) "
        "values (gen_random_uuid(), :d, :s, :day, 'REGISTERED')",
        d=driver_id,
        s=shift_id,
        day=local_today(),
    )
    online = await client.put("/api/v1/driver/availability", json={"online": True}, headers=driver)
    assert online.json() == {"availability": "ONLINE"}
    offline = await client.put(
        "/api/v1/driver/availability", json={"online": False}, headers=driver
    )
    assert offline.json() == {"availability": "OFFLINE"}


async def test_hub_managers_cannot_use_driver_endpoints(client: AsyncClient) -> None:
    manager = await login(client, HUB_MANAGER)
    assert (await client.get("/api/v1/driver/today", headers=manager)).status_code == 403
