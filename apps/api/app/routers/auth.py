from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
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
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidGoogleTokenError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
    build_user_read,
    confirm_password_reset,
    login_google_user,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    request_password_reset,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        return register_user(db, request)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        return login_user(db, request)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc






@router.post(
    "/google",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user with Google",
)
def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        return login_google_user(db, request)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
)
def password_reset_request(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> PasswordResetRequestResponse:
    return request_password_reset(db, request)


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
)
def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> PasswordResetConfirmResponse:
    try:
        return confirm_password_reset(db, request)
    except InvalidPasswordResetTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh auth tokens",
)
def refresh(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> RefreshTokenResponse:
    try:
        return refresh_tokens(db, request)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
)
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    return logout_user(db, request.refresh_token)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
)
def me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return build_user_read(current_user)
