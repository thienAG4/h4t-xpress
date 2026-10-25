"""System configuration (A-04..A-07): hubs, areas, shifts, validated settings, audit log."""

from httpx import AsyncClient

from tests.helpers import ADMIN, HUB_MANAGER, error_code, login, scalar


async def test_hubs_and_areas(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    areas = (await client.get("/api/v1/admin/areas", headers=admin)).json()
    assert areas and all(area["code"] for area in areas)

    created = await client.post(
        "/api/v1/admin/areas",
        json={
            "code": "TEST_AREA",
            "name": "Test area",
            "center_lat": 10.8,
            "center_lng": 106.7,
            "radius_km": 2,
        },
        headers=admin,
    )
    assert created.status_code == 201
    duplicate = await client.post(
        "/api/v1/admin/areas",
        json={
            "code": "TEST_AREA",
            "name": "Again",
            "center_lat": 10.8,
            "center_lng": 106.7,
            "radius_km": 2,
        },
        headers=admin,
    )
    assert error_code(duplicate) == "AREA_CODE_TAKEN"

    hubs = (await client.get("/api/v1/admin/hubs", headers=admin)).json()
    dian = next(hub for hub in hubs if hub["code"] == "DIAN")
    assert dian["drivers"] > 0 and dian["managers"] == 1
    body = {
        key: dian[key] for key in ("code", "name", "address", "lat", "lng", "area_id", "status")
    }
    renamed = await client.put(
        f"/api/v1/admin/hubs/{dian['id']}",
        json={**body, "name": "H4T Hub Di An (main)"},
        headers=admin,
    )
    assert renamed.status_code == 200 and renamed.json()["name"] == "H4T Hub Di An (main)"
    await client.put(f"/api/v1/admin/hubs/{dian['id']}", json=body, headers=admin)
    assert await scalar("select count(*) from audit_logs where action = 'hub.saved'") >= 2

    manager = await login(client, HUB_MANAGER)
    assert (await client.get("/api/v1/admin/hubs", headers=manager)).status_code == 403


async def test_shift_times_are_validated(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    shifts = (await client.get("/api/v1/admin/shifts", headers=admin)).json()
    morning = next(shift for shift in shifts if shift["code"] == "MORNING")
    wrong = await client.patch(
        f"/api/v1/admin/shifts/{morning['id']}", json={"end_time": "06:00:00"}, headers=admin
    )
    assert error_code(wrong) == "SHIFT_TIME_INVALID"
    bigger = await client.patch(
        f"/api/v1/admin/shifts/{morning['id']}",
        json={"capacity": morning["capacity"] + 2},
        headers=admin,
    )
    assert bigger.json()["capacity"] == morning["capacity"] + 2


async def test_settings_are_validated_and_audited(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    settings = (await client.get("/api/v1/admin/settings", headers=admin)).json()
    keys = {row["key"] for row in settings}
    assert "dispatch.weights" in keys and "sim.paused_drivers" not in keys

    bad_weights = await client.put(
        "/api/v1/admin/settings/dispatch.weights",
        json={"value": {"distance": 0.5, "load": 0.5, "performance": 0.5, "time_fit": 0.5}},
        headers=admin,
    )
    assert error_code(bad_weights) == "SETTING_INVALID"
    assert "add up to 1" in bad_weights.json()["error"]["message"]
    out_of_range = await client.put(
        "/api/v1/admin/settings/dispatch.max_rounds", json={"value": 99}, headers=admin
    )
    assert error_code(out_of_range) == "SETTING_INVALID"
    unknown = await client.put(
        "/api/v1/admin/settings/sim.paused_drivers", json={"value": {}}, headers=admin
    )
    assert error_code(unknown) == "SETTING_NOT_FOUND"

    saved = await client.put(
        "/api/v1/admin/settings/dispatch.max_rounds", json={"value": 4}, headers=admin
    )
    assert saved.status_code == 200 and saved.json()["value"] == 4
    await client.put("/api/v1/admin/settings/dispatch.max_rounds", json={"value": 3}, headers=admin)

    audit = (
        await client.get("/api/v1/admin/audit-logs", params={"action": "setting."}, headers=admin)
    ).json()
    assert audit["total"] >= 2
    assert audit["items"][0]["after"] == {"value": 3}
    assert audit["items"][0]["actor_name"]
