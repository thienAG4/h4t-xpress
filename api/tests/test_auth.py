"""Sign-in, refresh-token rotation, driver sign-up with OTP and password recovery."""

from httpx import AsyncClient

from tests.helpers import ADMIN, DEMO_PASSWORD, DRIVER, EXECUTIVE, error_code, login

REFRESH_COOKIE = "h4t_refresh"


async def _register(client: AsyncClient, phone: str, email: str) -> dict[str, str]:
    hubs = (await client.get("/api/v1/hubs")).json()
    response = await client.post(
        "/api/v1/auth/register/driver",
        json={
            "full_name": "Trần Thị Kiểm Thử",
            "phone": phone,
            "email": email,
            "password": "Secret#123",
            "hub_id": hubs[0]["id"],
            "vehicle_plate": "59x1-123.45",
            "license_no": "790000000001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# =============================== Sign-in ===============================


async def test_login_with_email_or_phone_returns_token_and_refresh_cookie(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"identifier": DRIVER.upper(), "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "DRIVER"
    assert "shift.register" in body["user"]["permissions"]
    assert REFRESH_COOKIE in response.cookies

    by_phone = await client.post(
        "/api/v1/auth/login", json={"identifier": "+84 120 000 001", "password": DEMO_PASSWORD}
    )
    assert by_phone.status_code == 200
    assert by_phone.json()["user"]["email"] == DRIVER


async def test_wrong_password_and_unknown_account_give_the_same_error(client: AsyncClient) -> None:
    wrong = await client.post("/api/v1/auth/login", json={"identifier": DRIVER, "password": "nope"})
    unknown = await client.post(
        "/api/v1/auth/login", json={"identifier": "ghost@demo.h4t", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert error_code(wrong) == error_code(unknown) == "INVALID_CREDENTIALS"


async def test_repeated_failed_logins_are_rate_limited(client: AsyncClient) -> None:
    for _ in range(10):
        await client.post("/api/v1/auth/login", json={"identifier": ADMIN, "password": "bad"})
    blocked = await client.post(
        "/api/v1/auth/login", json={"identifier": ADMIN, "password": DEMO_PASSWORD}
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["details"]["retry_after_seconds"] > 0


async def test_protected_endpoints_require_a_valid_access_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me")).status_code == 401
    garbage = await client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert garbage.status_code == 401
    assert error_code(garbage) == "TOKEN_EXPIRED"


async def test_demo_login_signs_in_each_role(client: AsyncClient) -> None:
    expected = {
        "DRIVER": "driver1@demo.h4t",
        "HUB_MANAGER": "hub.dian@demo.h4t",
        "EXECUTIVE": "exec@demo.h4t",
        "SYSTEM_ADMIN": "admin@demo.h4t",
    }
    for role, email in expected.items():
        response = await client.post("/api/v1/auth/demo-login", json={"role": role})
        assert response.status_code == 200
        assert response.json()["user"]["email"] == email


# =============================== Refresh tokens ===============================


async def test_refresh_rotates_the_cookie_and_detects_reuse(client: AsyncClient) -> None:
    await login(client, DRIVER)
    first_cookie = client.cookies[REFRESH_COOKIE]

    rotated = await client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    second_cookie = rotated.cookies[REFRESH_COOKIE]
    assert second_cookie != first_cookie

    # Replaying the old token is treated as theft: every session of the user ends.
    client.cookies.set(REFRESH_COOKIE, first_cookie, path="/api/v1/auth")
    replay = await client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    assert error_code(replay) == "REFRESH_REVOKED"

    client.cookies.set(REFRESH_COOKIE, second_cookie, path="/api/v1/auth")
    after_theft = await client.post("/api/v1/auth/refresh")
    assert after_theft.status_code == 401


async def test_logout_revokes_the_refresh_token(client: AsyncClient) -> None:
    await login(client, DRIVER)
    cookie = client.cookies[REFRESH_COOKIE]
    assert (await client.post("/api/v1/auth/logout")).status_code == 204

    client.cookies.set(REFRESH_COOKIE, cookie, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_refresh_without_cookie_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert error_code(response) == "REFRESH_MISSING"


# =============================== Sign-up with OTP ===============================


async def test_driver_sign_up_requires_otp_before_login(client: AsyncClient) -> None:
    sent = await _register(client, "0120555001", "signup1@example.com")
    assert sent["phone_hint"] == "0120****01"
    code = sent["demo_code"]
    assert code and len(code) == 6

    pending = await client.post(
        "/api/v1/auth/login", json={"identifier": "0120555001", "password": "Secret#123"}
    )
    assert pending.status_code == 403
    assert error_code(pending) == "ACCOUNT_NOT_VERIFIED"

    wrong_code = "000000" if code != "000000" else "111111"
    wrong = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": "0120555001", "code": wrong_code}
    )
    assert wrong.status_code == 422
    assert wrong.json()["error"]["details"]["attempts_left"] == 4

    verified = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+84120555001", "code": code}
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["status"] == "ACTIVE"
    assert verified.json()["user"]["driver"]["vehicle_plate"] == "59X1-123.45"


async def test_sign_up_rejects_weak_password_and_duplicate_phone(client: AsyncClient) -> None:
    hubs = (await client.get("/api/v1/hubs")).json()
    base = {
        "full_name": "Lê Văn B",
        "phone": "0120000001",
        "email": "weak@example.com",
        "hub_id": hubs[0]["id"],
        "vehicle_plate": "59A1-111.11",
        "license_no": "790000000002",
    }
    weak = await client.post("/api/v1/auth/register/driver", json={**base, "password": "abc"})
    assert weak.status_code == 422
    assert weak.json()["error"]["details"][0]["field"] == "password"

    taken = await client.post(
        "/api/v1/auth/register/driver", json={**base, "password": "Secret#123"}
    )
    assert taken.status_code == 409
    assert error_code(taken) == "PHONE_TAKEN"


async def test_otp_resend_has_a_cooldown(client: AsyncClient) -> None:
    await _register(client, "0120555002", "signup2@example.com")
    resend = await client.post("/api/v1/auth/otp/resend", json={"phone": "0120555002"})
    assert resend.status_code == 429
    assert error_code(resend) == "OTP_COOLDOWN"


# =============================== Password recovery ===============================


async def test_forgot_and_reset_password_for_a_regular_account(client: AsyncClient) -> None:
    sent = await _register(client, "0120555003", "signup3@example.com")
    await client.post(
        "/api/v1/auth/otp/verify", json={"phone": "0120555003", "code": sent["demo_code"]}
    )

    forgot = await client.post(
        "/api/v1/auth/password/forgot", json={"identifier": "signup3@example.com"}
    )
    assert forgot.status_code == 200
    reset = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "identifier": "0120555003",
            "code": forgot.json()["demo_code"],
            "new_password": "Changed#456",
        },
    )
    assert reset.status_code == 204

    old = await client.post(
        "/api/v1/auth/login", json={"identifier": "0120555003", "password": "Secret#123"}
    )
    assert old.status_code == 401
    await login(client, "0120555003", "Changed#456")


async def test_forgot_password_does_not_reveal_unknown_accounts(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/password/forgot", json={"identifier": "nobody@example.com"}
    )
    assert response.status_code == 200
    assert response.json() == {"sent": True, "phone_hint": None, "demo_code": None}


async def test_demo_account_password_cannot_be_reset(client: AsyncClient) -> None:
    forgot = await client.post("/api/v1/auth/password/forgot", json={"identifier": EXECUTIVE})
    reset = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "identifier": EXECUTIVE,
            "code": forgot.json()["demo_code"],
            "new_password": "Changed#456",
        },
    )
    assert reset.status_code == 403
    assert error_code(reset) == "DEMO_ACCOUNT_PROTECTED"
