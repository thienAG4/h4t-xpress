"""Permission checks on endpoints and the editable role-permission matrix (FR-A-02)."""

from httpx import AsyncClient

from tests.helpers import ADMIN, DRIVER, HUB_MANAGER, error_code, login


async def _role(client: AsyncClient, headers: dict[str, str], code: str) -> dict:
    roles = (await client.get("/api/v1/admin/roles", headers=headers)).json()
    return next(role for role in roles if role["code"] == code)


async def test_only_system_admins_reach_admin_endpoints(client: AsyncClient) -> None:
    for identifier in (DRIVER, HUB_MANAGER):
        headers = await login(client, identifier)
        response = await client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["details"] == ["user.manage"]

    admin = await login(client, ADMIN)
    assert (await client.get("/api/v1/admin/users", headers=admin)).status_code == 200


async def test_roles_list_the_default_matrix(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    roles = {r["code"]: r for r in (await client.get("/api/v1/admin/roles", headers=admin)).json()}
    assert set(roles) == {"DRIVER", "HUB_MANAGER", "EXECUTIVE", "SYSTEM_ADMIN"}
    assert len(roles["DRIVER"]["permissions"]) == 6
    assert roles["DRIVER"]["user_count"] >= 30
    permissions = (await client.get("/api/v1/admin/permissions", headers=admin)).json()
    assert len(permissions) == 19


async def test_changing_a_role_changes_new_tokens(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    hub_role = await _role(client, admin, "HUB_MANAGER")
    original = hub_role["permissions"]
    reduced = [code for code in original if code != "report.view"]

    updated = await client.put(
        f"/api/v1/admin/roles/{hub_role['id']}/permissions",
        json={"permissions": reduced, "force_relogin": True},
        headers=admin,
    )
    assert updated.status_code == 200
    assert "report.view" not in updated.json()["permissions"]

    me = await client.get("/api/v1/me", headers=await login(client, HUB_MANAGER))
    assert "report.view" not in me.json()["permissions"]

    restored = await client.put(
        f"/api/v1/admin/roles/{hub_role['id']}/permissions",
        json={"permissions": original},
        headers=admin,
    )
    assert sorted(restored.json()["permissions"]) == sorted(original)


async def test_system_admin_cannot_lose_role_management(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    admin_role = await _role(client, admin, "SYSTEM_ADMIN")
    response = await client.put(
        f"/api/v1/admin/roles/{admin_role['id']}/permissions",
        json={"permissions": ["audit.view"]},
        headers=admin,
    )
    assert response.status_code == 422
    assert error_code(response) == "LOCKOUT_PREVENTED"
    assert response.json()["error"]["details"] == ["role.manage", "user.manage"]


async def test_unknown_permission_codes_are_rejected(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    driver_role = await _role(client, admin, "DRIVER")
    response = await client.put(
        f"/api/v1/admin/roles/{driver_role['id']}/permissions",
        json={"permissions": ["shift.register", "fly.rocket"]},
        headers=admin,
    )
    assert response.status_code == 422
    assert error_code(response) == "UNKNOWN_PERMISSION"
