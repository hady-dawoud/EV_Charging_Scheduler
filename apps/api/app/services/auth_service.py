from __future__ import annotations

import logging
import uuid
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    hash_password_reset_token,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.auth_repository import (
    create_password_reset_token_record,
    create_refresh_token_record,
    create_user,
    get_active_password_reset_token_by_hash,
    get_user_by_google_sub,
    get_active_refresh_token_by_hash,
    get_user_by_email,
    get_user_by_id,
    mark_password_reset_token_used,
    revoke_active_refresh_tokens_for_user,
    revoke_refresh_token,
    update_user_google_sub,
    update_user_password_hash,
)
from app.services.email_service import EmailDeliveryError, send_password_reset_email
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    UserRead,
)


logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InvalidRefreshTokenError(ValueError):
    pass


class InvalidGoogleTokenError(ValueError):
    pass


class InvalidPasswordResetTokenError(ValueError):
    pass


class InactiveUserError(ValueError):
    pass


def build_user_read(user: User) -> UserRead:
    return UserRead(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
    )


def _refresh_expiry() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days,
    )


def _password_reset_expiry() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_token_expire_minutes,
    )


def _issue_token_pair(
    db: Session,
    *,
    user: User,
    device_id: str | None = None,
) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token()

    create_refresh_token_record(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=_refresh_expiry(),
        device_id=device_id,
    )

    return access_token, refresh_token


def register_user(db: Session, request: RegisterRequest) -> AuthResponse:
    existing_user = get_user_by_email(db, request.email)

    if existing_user is not None:
        raise EmailAlreadyRegisteredError("Email is already registered")

    user = create_user(
        db,
        email=request.email,
        full_name=request.full_name,
        password_hash=hash_password(request.password),
    )

    access_token, refresh_token = _issue_token_pair(db, user=user)

    return AuthResponse(
        user=build_user_read(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


def login_user(db: Session, request: LoginRequest) -> AuthResponse:
    user = get_user_by_email(db, request.email)

    if user is None or not verify_password(request.password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    access_token, refresh_token = _issue_token_pair(
        db,
        user=user,
        device_id=request.device_id,
    )

    return AuthResponse(
        user=build_user_read(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )




def login_google_user(db: Session, request: GoogleLoginRequest) -> AuthResponse:
    settings = get_settings()

    if not settings.google_web_client_id:
        raise InvalidGoogleTokenError("Google login is not configured")

    try:
        id_info = google_id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            settings.google_web_client_id,
        )
    except ValueError as exc:
        raise InvalidGoogleTokenError("Invalid Google ID token") from exc

    google_sub = str(id_info.get("sub") or "")
    email = str(id_info.get("email") or "").lower()
    full_name = str(id_info.get("name") or "").strip()
    email_verified = bool(id_info.get("email_verified"))

    if not google_sub or not email or not email_verified:
        raise InvalidGoogleTokenError("Google account email is not verified")

    if not full_name:
        full_name = email.split("@", maxsplit=1)[0]

    user = get_user_by_google_sub(db, google_sub)

    if user is None:
        existing_user = get_user_by_email(db, email)

        if existing_user is not None:
            if not existing_user.is_active:
                raise InactiveUserError("User account is inactive")

            user = update_user_google_sub(
                db,
                user=existing_user,
                google_sub=google_sub,
            )
        else:
            user = create_user(
                db,
                email=email,
                full_name=full_name,
                password_hash=hash_password(create_refresh_token()),
                google_sub=google_sub,
            )

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    access_token, refresh_token = _issue_token_pair(
        db,
        user=user,
        device_id=request.device_id,
    )

    return AuthResponse(
        user=build_user_read(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


def refresh_tokens(
    db: Session,
    request: RefreshTokenRequest,
) -> RefreshTokenResponse:
    now = datetime.now(timezone.utc)
    token_hash = hash_refresh_token(request.refresh_token)
    refresh_token_record = get_active_refresh_token_by_hash(db, token_hash)

    if refresh_token_record is None:
        raise InvalidRefreshTokenError("Invalid refresh token")

    if refresh_token_record.expires_at <= now:
        raise InvalidRefreshTokenError("Refresh token has expired")

    user = get_user_by_id(db, refresh_token_record.user_id)

    if user is None:
        raise InvalidRefreshTokenError("Refresh token user no longer exists")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    revoke_refresh_token(
        db,
        token_hash=token_hash,
        revoked_at=now,
    )

    access_token, new_refresh_token = _issue_token_pair(
        db,
        user=user,
        device_id=request.device_id or refresh_token_record.device_id,
    )

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


def logout_user(db: Session, refresh_token: str) -> LogoutResponse:
    token_hash = hash_refresh_token(refresh_token)

    revoke_refresh_token(
        db,
        token_hash=token_hash,
        revoked_at=datetime.now(timezone.utc),
    )

    return LogoutResponse(success=True)


def request_password_reset(
    db: Session,
    request: PasswordResetRequest,
) -> PasswordResetRequestResponse:
    settings = get_settings()
    user = get_user_by_email(db, request.email)

    response = PasswordResetRequestResponse(
        success=True,
        message="If an account exists for that email, password reset instructions have been generated.",
    )

    if user is None or not user.is_active:
        return response

    reset_token = create_password_reset_token()

    create_password_reset_token_record(
        db,
        user_id=user.id,
        token_hash=hash_password_reset_token(reset_token),
        expires_at=_password_reset_expiry(),
    )

    if settings.password_reset_email_enabled:
        try:
            reset_url = (
                f"{settings.password_reset_web_url.rstrip('/')}"
                f"/?reset_token={quote(reset_token)}"
            )

            send_password_reset_email(
                recipient_email=user.email,
                reset_url=reset_url,
                expires_minutes=settings.password_reset_token_expire_minutes,
            )
        except EmailDeliveryError:
            logger.exception("Password reset email delivery failed")

    if settings.password_reset_return_token_for_development:
        response.development_reset_token = reset_token

    return response


def confirm_password_reset(
    db: Session,
    request: PasswordResetConfirmRequest,
) -> PasswordResetConfirmResponse:
    now = datetime.now(timezone.utc)
    token_hash = hash_password_reset_token(request.token)
    reset_token_record = get_active_password_reset_token_by_hash(db, token_hash)

    if reset_token_record is None:
        raise InvalidPasswordResetTokenError("Invalid or already used password reset token")

    if reset_token_record.expires_at <= now:
        raise InvalidPasswordResetTokenError("Password reset token has expired")

    user = get_user_by_id(db, reset_token_record.user_id)

    if user is None:
        raise InvalidPasswordResetTokenError("Password reset token user no longer exists")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    update_user_password_hash(
        db,
        user=user,
        password_hash=hash_password(request.new_password),
    )

    mark_password_reset_token_used(
        db,
        token_hash=token_hash,
        used_at=now,
    )

    revoke_active_refresh_tokens_for_user(
        db,
        user_id=user.id,
        revoked_at=now,
    )

    return PasswordResetConfirmResponse(success=True)


def get_current_user_from_subject(db: Session, subject: str) -> User:
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise InvalidCredentialsError("Invalid token subject") from exc

    user = get_user_by_id(db, user_id)

    if user is None:
        raise InvalidCredentialsError("User not found")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    return user
