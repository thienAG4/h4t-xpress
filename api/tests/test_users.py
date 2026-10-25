"""Account management by system admins (FR-A-01) and the /me profile."""

from httpx import AsyncClient

from tests.helpers import ADMIN, DRIVER, error_code, login, scalar


async def _hub_id(client: AsyncClient, code: str = "DIAN") -> str:
    hubs = (await client.get("/api/v1/hubs")).json()
    return next(hub["id"] for hub in hubs if hub["code"] == code)


async def test_list_users_supports_filters_and_paging(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    drivers = await client.get(
        "/api/v1/admin/users", params={"role": "DRIVER", "page_size": 5}, headers=admin
    )
    body = drivers.json()
    assert body["total"] >= 30
    assert len(body["items"]) == 5
    assert all(user["role"] == "DRIVER" and user["driver"] for user in body["items"])

    search = await client.get("/api/v1/admin/users", params={"q": "hub.dian"}, headers=admin)
    assert [user["email"] for user in search.json()["items"]] == ["hub.dian@demo.h4t"]


async def test_create_user_validates_role_rules(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    no_hub = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Quản Lý Mới",
            "email": "manager.new@example.com",
            "role": "HUB_MANAGER",
        },
        headers=admin,
    )
    assert no_hub.status_code == 422
    assert error_code(no_hub) == "HUB_REQUIRED"

    driver_without_vehicle = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Tài Xế Mới",
            "email": "driver.new@example.com",
            "role": "DRIVER",
            "hub_id": await _hub_id(client),
        },
        headers=admin,
    )
    assert error_code(driver_without_vehicle) == "DRIVER_FIELDS_REQUIRED"

    duplicate = await client.post(
        "/api/v1/admin/users",
        json={"full_name": "Copy", "email": "EXEC@demo.h4t", "role": "EXECUTIVE"},
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "EMAIL_TAKEN"


async def test_created_user_gets_a_temporary_password_and_audit_entry(
    client: AsyncClient,
) -> None:
    admin = await login(client, ADMIN)
    created = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Phạm Thị Điều Phối",
            "email": "dispatcher@example.com",
            "phone": "0120777001",
            "role": "HUB_MANAGER",
            "hub_id": await _hub_id(client, "THUDUC"),
        },
        headers=admin,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["user"]["hub_name"] == "H4T Hub Thủ Đức"
    temporary = body["temporary_password"]
    assert temporary

    await login(client, "dispatcher@example.com", temporary)
    audit = await scalar(
        "select count(*) from audit_logs where action = 'user.created' and entity_id = :id",
        id=body["user"]["id"],
    )
    assert audit == 1


async def test_lock_and_unlock_a_regular_account(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    created = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Người Bị Khoá",
            "email": "locked@example.com",
            "role": "EXECUTIVE",
            "password": "Secret#123",
        },
        headers=admin,
    )
    user_id = created.json()["user"]["id"]

    locked = await client.post(f"/api/v1/admin/users/{user_id}/lock", headers=admin)
    assert locked.json()["status"] == "LOCKED"
    denied = await client.post(
        "/api/v1/auth/login", json={"identifier": "locked@example.com", "password": "Secret#123"}
    )
    assert error_code(denied) == "ACCOUNT_LOCKED"

    await client.post(f"/api/v1/admin/users/{user_id}/unlock", headers=admin)
    await login(client, "locked@example.com", "Secret#123")


async def test_demo_accounts_and_self_are_protected(client: AsyncClient) -> None:
    admin = await login(client, ADMIN)
    me = (await client.get("/api/v1/me", headers=admin)).json()
    self_lock = await client.post(f"/api/v1/admin/users/{me['id']}/lock", headers=admin)
    assert error_code(self_lock) == "CANNOT_LOCK_SELF"

    driver_id = await scalar("select id from users where email = :email", email=DRIVER)
    demo_lock = await client.post(f"/api/v1/admin/users/{driver_id}/lock", headers=admin)
    assert demo_lock.status_code == 403
    assert error_code(demo_lock) == "DEMO_ACCOUNT_PROTECTED"
    demo_reset = await client.post(f"/api/v1/admin/users/{driver_id}/reset-password", headers=admin)
    assert error_code(demo_reset) == "DEMO_ACCOUNT_PROTECTED"


async def test_demo_account_can_be_edited_when_email_and_role_are_unchanged(
    client: AsyncClient,
) -> None:
    admin = await login(client, ADMIN)
    driver_id = await scalar("select id from users where email = :email", email=DRIVER)
    edited = await client.patch(
        f"/api/v1/admin/users/{driver_id}",
        json={"full_name": "Tài Xế Một", "email": DRIVER, "role": "DRIVER"},
        headers=admin,
    )
    assert edited.status_code == 200
    assert edited.json()["full_name"] == "Tài Xế Một"

    renamed = await client.patch(
        f"/api/v1/admin/users/{driver_id}", json={"email": "new@example.com"}, headers=admin
    )
    assert error_code(renamed) == "DEMO_ACCOUNT_PROTECTED"


async def test_profile_update_and_password_rules(client: AsyncClient) -> None:
    driver = await login(client, DRIVER)
    updated = await client.patch(
        "/api/v1/me", json={"address": "1 Võ Văn Ngân, P. Thủ Đức, TP.HCM"}, headers=driver
    )
    assert updated.status_code == 200
    assert updated.json()["address"].startswith("1 Võ Văn Ngân")

    change = await client.post(
        "/api/v1/me/password",
        json={"current_password": "Demo@12345", "new_password": "Another#789"},
        headers=driver,
    )
    assert error_code(change) == "DEMO_ACCOUNT_PROTECTED"
