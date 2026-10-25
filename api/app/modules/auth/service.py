"""Sign-up with OTP, sign-in, refresh-token rotation and password recovery (SPEC §5.2)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    Conflict,
    Forbidden,
    NotFound,
    TooManyRequests,
    Unauthorized,
    ValidationFailed,
)
from app.core.rate_limit import RateLimiter
from app.core.security import (
    create_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import OtpCode, OtpPurpose, RefreshToken
from app.modules.auth.otp import mask_phone, otp_sender
from app.modules.auth.schemas import OtpSentOut, RegisterDriverIn
from app.modules.hubs.models import Hub
from app.modules.rbac.models import Role, RoleCode
from app.modules.rbac.service import get_permission_codes, get_role_by_code
from app.modules.users.models import DriverProfile, User, UserStatus
from app.modules.users.schemas import MeOut
from app.modules.users.service import get_me, revoke_sessions

logger = logging.getLogger(__name__)

login_limiter = RateLimiter(get_settings().login_attempts_per_minute, 60)
otp_limiter = RateLimiter(10, 60)

DEMO_ACCOUNTS = {
    RoleCode.DRIVER: "driver1@demo.h4t",
    RoleCode.HUB_MANAGER: "hub.dian@demo.h4t",
    RoleCode.EXECUTIVE: "exec@demo.h4t",
    RoleCode.SYSTEM_ADMIN: "admin@demo.h4t",
}


@dataclass
class SessionTokens:
    access_token: str
    expires_in: int
    refresh_token: str
    user: MeOut


def _now() -> datetime:
    return datetime.now(UTC)


async def _find_by_identifier(session: AsyncSession, identifier: str) -> User | None:
    column = func.lower(User.email) if "@" in identifier else User.phone
    return await session.scalar(select(User).where(column == identifier))


# =============================== Tokens ===============================


async def issue_tokens(
    session: AsyncSession, user: User, *, user_agent: str | None = None
) -> SessionTokens:
    """Create an access token and a new refresh token (stored hashed)."""
    settings = get_settings()
    role_code = await session.scalar(select(Role.code).where(Role.id == user.role_id))
    permissions = await get_permission_codes(session, user.role_id)
    access_token, expires_in = create_access_token(
        user_id=user.id, role=role_code or "", hub_id=user.hub_id, permissions=permissions
    )
    refresh_plain = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_plain),
            expires_at=_now() + timedelta(days=settings.refresh_token_days),
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    await session.commit()
    return SessionTokens(access_token, expires_in, refresh_plain, await get_me(session, user.id))


def _ensure_can_sign_in(user: User) -> None:
    if user.status == UserStatus.LOCKED:
        raise Forbidden("This account is locked", code="ACCOUNT_LOCKED")
    if user.status == UserStatus.PENDING_VERIFICATION:
        raise Forbidden("Please verify your phone number first", code="ACCOUNT_NOT_VERIFIED")


async def login(
    session: AsyncSession, identifier: str, password: str, *, ip: str, user_agent: str | None
) -> SessionTokens:
    login_limiter.hit(f"{ip}:{identifier}")
    user = await _find_by_identifier(session, identifier)
    # Same error for unknown account and wrong password, to avoid account enumeration.
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthorized("Phone/e-mail or password is incorrect", code="INVALID_CREDENTIALS")
    _ensure_can_sign_in(user)
    user.last_login_at = _now()
    logger.info("[login] user=%s", user.id)
    return await issue_tokens(session, user, user_agent=user_agent)


async def demo_login(
    session: AsyncSession, role: RoleCode, *, user_agent: str | None
) -> SessionTokens:
    """One-click login for the public demo (only when DEMO_MODE is on)."""
    user = await session.scalar(select(User).where(User.email == DEMO_ACCOUNTS[role]))
    if user is None:
        raise NotFound("Demo account not found, please reseed", code="DEMO_ACCOUNT_MISSING")
    _ensure_can_sign_in(user)
    user.last_login_at = _now()
    return await issue_tokens(session, user, user_agent=user_agent)


async def refresh(
    session: AsyncSession, refresh_plain: str | None, *, user_agent: str | None
) -> SessionTokens:
    """Rotate the refresh token. Reusing an old token revokes every session of the user."""
    if not refresh_plain:
        raise Unauthorized("No session", code="REFRESH_MISSING")
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_plain))
    )
    if token is None:
        raise Unauthorized("Session not found", code="REFRESH_INVALID")
    if token.revoked_at is not None:
        if token.replaced_by is not None:
            await revoke_sessions(session, token.user_id)
            await session.commit()
            logger.warning("[refresh] reuse detected for user=%s, sessions revoked", token.user_id)
        raise Unauthorized("Session has ended, please sign in again", code="REFRESH_REVOKED")
    if token.expires_at <= _now():
        raise Unauthorized("Session expired, please sign in again", code="REFRESH_EXPIRED")

    user = await session.get(User, token.user_id)
    if user is None:
        raise Unauthorized("Session not found", code="REFRESH_INVALID")
    _ensure_can_sign_in(user)

    tokens = await issue_tokens(session, user, user_agent=user_agent)
    new_id = await session.scalar(
        select(RefreshToken.id).where(RefreshToken.token_hash == hash_token(tokens.refresh_token))
    )
    token.revoked_at = _now()
    token.replaced_by = new_id
    await session.commit()
    return tokens


async def logout(session: AsyncSession, refresh_plain: str | None) -> None:
    if not refresh_plain:
        return
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(refresh_plain))
        .values(revoked_at=_now())
    )
    await session.commit()


# =============================== OTP ===============================


async def _issue_otp(session: AsyncSession, user: User, purpose: OtpPurpose) -> OtpSentOut:
    settings = get_settings()
    latest = await session.scalar(
        select(OtpCode.created_at)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    cooldown = timedelta(seconds=settings.otp_resend_cooldown_seconds)
    if latest is not None and latest + cooldown > _now():
        wait = int((latest + cooldown - _now()).total_seconds()) + 1
        raise TooManyRequests(
            "Please wait before requesting a new code",
            code="OTP_COOLDOWN",
            details={"retry_after_seconds": wait},
        )

    code = generate_otp_code()
    now = _now()
    session.add(
        OtpCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=hash_token(code),
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
            created_at=now,
        )
    )
    await session.commit()
    otp_sender.send(user.phone or "", code)
    return OtpSentOut(
        phone_hint=mask_phone(user.phone),
        expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        resend_available_at=now + cooldown,
        demo_code=code if settings.demo_mode else None,
    )


async def _consume_otp(session: AsyncSession, user: User, purpose: OtpPurpose, code: str) -> None:
    """Check the latest code: expiry, attempt limit, then value (SPEC §5.2)."""
    settings = get_settings()
    otp = await session.scalar(
        select(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    if otp is None or otp.consumed_at is not None:
        raise ValidationFailed("No active code, please request a new one", code="OTP_NOT_FOUND")
    if otp.expires_at <= _now():
        raise ValidationFailed("This code has expired", code="OTP_EXPIRED")
    if otp.attempts >= settings.otp_max_attempts:
        raise ValidationFailed("Too many wrong codes, request a new one", code="OTP_LOCKED")
    if otp.code_hash != hash_token(code):
        otp.attempts += 1
        await session.commit()
        raise ValidationFailed(
            "The code is incorrect",
            code="OTP_INVALID",
            details={"attempts_left": max(settings.otp_max_attempts - otp.attempts, 0)},
        )
    otp.consumed_at = _now()


# =============================== Sign-up ===============================


async def register_driver(session: AsyncSession, data: RegisterDriverIn) -> OtpSentOut:
    """Create a PENDING_VERIFICATION driver and send the first OTP (D-01 -> D-03)."""
    email = data.email.lower()
    if await session.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise Conflict("This e-mail is already used", code="EMAIL_TAKEN")
    if await session.scalar(select(User.id).where(User.phone == data.phone)):
        raise Conflict("This phone number is already used", code="PHONE_TAKEN")
    hub = await session.get(Hub, data.hub_id)
    if hub is None:
        raise NotFound("Hub not found", code="HUB_NOT_FOUND")

    role = await get_role_by_code(session, RoleCode.DRIVER)
    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role_id=role.id,
        hub_id=hub.id,
        national_id=data.national_id,
        status=UserStatus.PENDING_VERIFICATION,
    )
    session.add(user)
    await session.flush()
    session.add(
        DriverProfile(
            user_id=user.id,
            vehicle_plate=data.vehicle_plate.upper(),
            license_no=data.license_no,
            home_area_id=hub.area_id,
        )
    )
    await session.commit()
    logger.info("[register_driver] user=%s hub=%s", user.id, hub.code)
    return await _issue_otp(session, user, OtpPurpose.REGISTER)


async def verify_registration(
    session: AsyncSession, phone: str, code: str, *, user_agent: str | None
) -> SessionTokens:
    otp_limiter.hit(f"verify:{phone}")
    user = await session.scalar(select(User).where(User.phone == phone))
    if user is None or user.status != UserStatus.PENDING_VERIFICATION:
        raise ValidationFailed("Nothing to verify for this number", code="OTP_NOT_FOUND")
    await _consume_otp(session, user, OtpPurpose.REGISTER, code)
    user.status = UserStatus.ACTIVE
    user.last_login_at = _now()
    return await issue_tokens(session, user, user_agent=user_agent)


async def resend_otp(session: AsyncSession, phone: str, purpose: OtpPurpose) -> OtpSentOut:
    user = await session.scalar(select(User).where(User.phone == phone))
    expected = (
        UserStatus.PENDING_VERIFICATION if purpose == OtpPurpose.REGISTER else UserStatus.ACTIVE
    )
    if user is None or user.status != expected:
        raise ValidationFailed("No code can be sent to this number", code="OTP_NOT_AVAILABLE")
    return await _issue_otp(session, user, purpose)


# =============================== Password recovery ===============================


async def forgot_password(
    session: AsyncSession, identifier: str, *, ip: str
) -> tuple[bool, OtpSentOut | None]:
    """Send a reset code. Unknown accounts get the same answer (no enumeration)."""
    otp_limiter.hit(f"forgot:{ip}")
    user = await _find_by_identifier(session, identifier)
    if user is None or user.status != UserStatus.ACTIVE or not user.phone:
        return True, None
    return True, await _issue_otp(session, user, OtpPurpose.RESET_PASSWORD)


async def reset_password(
    session: AsyncSession, identifier: str, code: str, new_password: str
) -> None:
    otp_limiter.hit(f"reset:{identifier}")
    user = await _find_by_identifier(session, identifier)
    if user is None:
        raise ValidationFailed("No active code, please request a new one", code="OTP_NOT_FOUND")
    if get_settings().demo_mode and user.email.endswith("@demo.h4t"):
        raise Forbidden("Demo account passwords cannot be changed", code="DEMO_ACCOUNT_PROTECTED")
    await _consume_otp(session, user, OtpPurpose.RESET_PASSWORD, code)
    user.password_hash = hash_password(new_password)
    await revoke_sessions(session, user.id)
    await session.commit()


def reset_limiters() -> None:
    """Used by tests to start each case with a clean limiter state."""
    login_limiter.reset()
    otp_limiter.reset()
