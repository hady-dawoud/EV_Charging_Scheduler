from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import RefreshToken, User


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    return db.execute(statement).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.execute(statement).scalar_one_or_none()


def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    password_hash: str,
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=password_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_refresh_token_record(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    device_id: str | None = None,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_id=device_id,
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token


def get_active_refresh_token_by_hash(
    db: Session,
    token_hash: str,
) -> RefreshToken | None:
    statement = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
    )
    return db.execute(statement).scalar_one_or_none()


def revoke_refresh_token(
    db: Session,
    *,
    token_hash: str,
    revoked_at: datetime,
) -> bool:
    refresh_token = get_active_refresh_token_by_hash(db, token_hash)

    if refresh_token is None:
        return False

    refresh_token.revoked_at = revoked_at
    db.add(refresh_token)
    db.commit()
    return True
