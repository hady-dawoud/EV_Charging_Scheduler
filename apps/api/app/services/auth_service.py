from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.auth_repository import (
    create_refresh_token_record,
    create_user,
    get_active_refresh_token_by_hash,
    get_user_by_email,
    get_user_by_id,
    revoke_refresh_token,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    UserRead,
)


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InvalidRefreshTokenError(ValueError):
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
