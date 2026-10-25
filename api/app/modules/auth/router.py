"""Authentication endpoints. The refresh token lives in an httpOnly cookie (SPEC §5.2)."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.deps import DbSession, client_ip, require_demo_mode
from app.core.errors import AppError, error_response
from app.modules.auth import service
from app.modules.auth.schemas import (
    DemoLoginIn,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    OtpSentOut,
    RegisterDriverIn,
    ResendOtpIn,
    ResetPasswordIn,
    TokenOut,
    VerifyOtpIn,
)

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_PATH = "/api/v1/auth"
RefreshCookie = Annotated[str | None, Cookie(alias=get_settings().refresh_cookie_name)]


def _token_response(response: Response, tokens: service.SessionTokens) -> TokenOut:
    settings = get_settings()
    response.set_cookie(
        settings.refresh_cookie_name,
        tokens.refresh_token,
        max_age=settings.refresh_token_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=COOKIE_PATH,
    )
    return TokenOut(
        access_token=tokens.access_token, expires_in=tokens.expires_in, user=tokens.user
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(get_settings().refresh_cookie_name, path=COOKIE_PATH)


# =============================== Sign-up ===============================


@router.post("/register/driver", response_model=OtpSentOut, status_code=201)
async def register_driver(data: RegisterDriverIn, session: DbSession) -> OtpSentOut:
    """
    Driver sign-up (D-01). The account stays PENDING_VERIFICATION until the OTP is checked.

    Inputs: {"full_name", "phone", "email", "password", "hub_id", "vehicle_plate", "license_no"}
    Outputs: {"phone_hint", "expires_at", "resend_available_at", "demo_code" (demo only)}
    Errors: EMAIL_TAKEN, PHONE_TAKEN, HUB_NOT_FOUND, VALIDATION_ERROR
    """
    return await service.register_driver(session, data)


@router.post("/otp/verify", response_model=TokenOut)
async def verify_otp(
    data: VerifyOtpIn, request: Request, response: Response, session: DbSession
) -> TokenOut:
    """
    Check the sign-up code (D-03) and sign the driver in.

    Errors: OTP_INVALID (details.attempts_left), OTP_EXPIRED, OTP_LOCKED, OTP_NOT_FOUND
    """
    tokens = await service.verify_registration(
        session, data.phone, data.code, user_agent=request.headers.get("user-agent")
    )
    return _token_response(response, tokens)


@router.post("/otp/resend", response_model=OtpSentOut)
async def resend_otp(data: ResendOtpIn, session: DbSession) -> OtpSentOut:
    """Errors: OTP_COOLDOWN (429, details.retry_after_seconds), OTP_NOT_AVAILABLE."""
    return await service.resend_otp(session, data.phone, data.purpose)


# =============================== Sessions ===============================


@router.post("/login", response_model=TokenOut)
async def login(
    data: LoginIn, request: Request, response: Response, session: DbSession
) -> TokenOut:
    """
    Sign in with e-mail or phone number (FR-A-03).

    Inputs: {"identifier": "driver1@demo.h4t" | "0120000001", "password": "..."}
    Outputs: {"access_token", "token_type", "expires_in", "user": MeOut} + refresh cookie
    Errors: INVALID_CREDENTIALS, ACCOUNT_LOCKED, ACCOUNT_NOT_VERIFIED, TOO_MANY_REQUESTS
    """
    tokens = await service.login(
        session,
        data.identifier,
        data.password,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _token_response(response, tokens)


@router.post("/demo-login", response_model=TokenOut, dependencies=[Depends(require_demo_mode)])
async def demo_login(
    data: DemoLoginIn, request: Request, response: Response, session: DbSession
) -> TokenOut:
    """One-click sign-in as the demo account of a role (demo deployments only)."""
    tokens = await service.demo_login(
        session, data.role, user_agent=request.headers.get("user-agent")
    )
    return _token_response(response, tokens)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request, response: Response, session: DbSession, refresh_token: RefreshCookie = None
) -> TokenOut | JSONResponse:
    """
    Exchange the refresh cookie for a new access token; the cookie is rotated.

    Errors: REFRESH_MISSING, REFRESH_INVALID, REFRESH_REVOKED, REFRESH_EXPIRED
    (the cookie is cleared on any error so the browser stops sending it)
    """
    try:
        tokens = await service.refresh(
            session, refresh_token, user_agent=request.headers.get("user-agent")
        )
    except AppError as exc:
        failed = error_response(exc)
        _clear_cookie(failed)
        return failed
    return _token_response(response, tokens)


@router.post("/logout", status_code=204)
async def logout(session: DbSession, refresh_token: RefreshCookie = None) -> Response:
    await service.logout(session, refresh_token)
    response = Response(status_code=204)
    _clear_cookie(response)
    return response


# =============================== Password recovery ===============================


@router.post("/password/forgot", response_model=ForgotPasswordOut)
async def forgot_password(
    data: ForgotPasswordIn, request: Request, session: DbSession
) -> ForgotPasswordOut:
    """Always answers `sent: true`; a code is only issued for an existing active account."""
    _, otp = await service.forgot_password(session, data.identifier, ip=client_ip(request))
    return ForgotPasswordOut(
        phone_hint=otp.phone_hint if otp else None, demo_code=otp.demo_code if otp else None
    )


@router.post("/password/reset", status_code=204)
async def reset_password(data: ResetPasswordIn, session: DbSession) -> Response:
    """Errors: OTP_INVALID, OTP_EXPIRED, OTP_LOCKED, DEMO_ACCOUNT_PROTECTED."""
    await service.reset_password(session, data.identifier, data.code, data.new_password)
    return Response(status_code=204)
