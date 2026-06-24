from jose import JWTError
from sqlalchemy.orm import Session

from app.core.domain_errors import BadRequestError, UnauthorizedError
from app.core.redis import is_refresh_token_revoked, revoke_refresh_token
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services.tenant_membership_service import assert_active_tenant_membership
from app.schemas.auth import UserCreate, UserLogin
from app.services.user_service import invalidate_users_list_cache


def get_user_by_email(db: Session, email: str, tenant_id: int) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )


def create_user(
    db: Session, user_data: UserCreate, tenant_id: int, *, role: str = "user"
) -> User:
    existing_user = get_user_by_email(db, user_data.email, tenant_id)

    if existing_user:
        raise BadRequestError("User with this email already exists")

    hashed_password = hash_password(user_data.password)

    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        tenant_id=tenant_id,
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    invalidate_users_list_cache(tenant_id)

    return user


def authenticate_user(db: Session, login_data: UserLogin, tenant_id: int) -> User:
    user = get_user_by_email(db, login_data.email, tenant_id)

    if not user:
        raise UnauthorizedError("Invalid email or password")

    if not verify_password(login_data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Inactive user")

    return user


def login_user(db: Session, login_data: UserLogin, tenant_id: int) -> tuple[str, str]:
    user = authenticate_user(db, login_data, tenant_id)

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        token_version=user.token_version,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        token_version=user.token_version,
    )

    return access_token, refresh_token


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    payload = _decode_refresh_token(refresh_token)
    user = _get_active_user_from_refresh_payload(db, payload)

    if not revoke_refresh_token(payload["jti"], payload["exp"], require_new=True):
        raise UnauthorizedError("Refresh token has been revoked")

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        token_version=user.token_version,
    )
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        token_version=user.token_version,
    )

    return access_token, new_refresh_token


def logout_user(refresh_token: str) -> None:
    payload = _decode_refresh_token(refresh_token)
    revoke_refresh_token(payload["jti"], payload["exp"])


def _decode_refresh_token(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise UnauthorizedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    jti = payload.get("jti")
    expires_at = payload.get("exp")
    tenant_id = payload.get("tenant_id")
    token_version = payload.get("token_version")

    if not jti or not expires_at or tenant_id is None or token_version is None:
        raise UnauthorizedError("Invalid refresh token")

    if is_refresh_token_revoked(jti):
        raise UnauthorizedError("Refresh token has been revoked")

    return payload


def _get_active_user_from_refresh_payload(db: Session, payload: dict) -> User:
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if user_id is None or tenant_id is None:
        raise UnauthorizedError("Invalid refresh token")

    try:
        parsed_user_id = int(user_id)
        parsed_tenant_id = int(tenant_id)
    except ValueError:
        raise UnauthorizedError("Invalid refresh token")

    user = (
        db.query(User)
        .filter(User.id == parsed_user_id, User.tenant_id == parsed_tenant_id)
        .first()
    )

    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    assert_active_tenant_membership(user)

    refresh_token_version = payload.get("token_version")
    if refresh_token_version != user.token_version:
        raise UnauthorizedError("Refresh token has been revoked")

    return user
