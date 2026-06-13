import hmac
import secrets
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.ids import uuid7


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        token.encode("utf-8"),
        sha256,
    ).hexdigest()


def verify_password_reset_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_password_reset_token(token), token_hash)


def create_access_token(
    subject: str,
    tenant_id: int,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "token_version": token_version,
        "exp": expire,
        "type": "access",
        "jti": str(uuid7()),
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    subject: str,
    tenant_id: int,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(days=settings.refresh_token_expire_days)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "token_version": token_version,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid7()),
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
