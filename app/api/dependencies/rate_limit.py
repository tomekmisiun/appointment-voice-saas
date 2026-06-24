import hashlib
import logging

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger("app.rate_limit")

REDIS_UNAVAILABLE_DETAIL = "Service temporarily unavailable"


def enforce_rate_limit_counter(
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    try:
        current_count = redis_client.incr(key)

        if current_count == 1:
            redis_client.expire(key, window_seconds)
    except RedisError as exc:
        logger.warning("rate_limit_redis_unavailable key=%s", key, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REDIS_UNAVAILABLE_DETAIL,
        ) from exc

    if current_count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )


def rate_limit(
    limit: int | None = None,
    window_seconds: int | None = None,
    *,
    key_prefix: str = "rate_limit",
):
    if limit is not None and limit <= 0:
        raise ValueError("rate limit must be greater than 0")

    if window_seconds is not None and window_seconds <= 0:
        raise ValueError("rate limit window_seconds must be greater than 0")

    def dependency(request: Request):
        effective_limit = (
            limit if limit is not None else settings.rate_limit_default_limit
        )
        effective_window_seconds = (
            window_seconds
            if window_seconds is not None
            else settings.rate_limit_default_window_seconds
        )
        client_ip = get_client_ip(request)
        key = f"{key_prefix}:{client_ip}"

        enforce_rate_limit_counter(
            key=key,
            limit=effective_limit,
            window_seconds=effective_window_seconds,
        )

    return dependency


def auth_login_rate_limit():
    return rate_limit(
        limit=settings.auth_login_rate_limit_limit,
        window_seconds=settings.auth_login_rate_limit_window_seconds,
        key_prefix="rate_limit:auth_login",
    )


def auth_register_rate_limit():
    return rate_limit(
        limit=settings.auth_register_rate_limit_limit,
        window_seconds=settings.auth_register_rate_limit_window_seconds,
        key_prefix="rate_limit:auth_register",
    )


def tenant_signup_rate_limit():
    return rate_limit(
        limit=settings.tenant_signup_rate_limit_limit,
        window_seconds=settings.tenant_signup_rate_limit_window_seconds,
        key_prefix="rate_limit:tenant_signup",
    )


def auth_refresh_rate_limit():
    return rate_limit(
        limit=settings.auth_refresh_rate_limit_limit,
        window_seconds=settings.auth_refresh_rate_limit_window_seconds,
        key_prefix="rate_limit:auth_refresh",
    )


def auth_logout_rate_limit():
    return rate_limit(
        limit=settings.auth_logout_rate_limit_limit,
        window_seconds=settings.auth_logout_rate_limit_window_seconds,
        key_prefix="rate_limit:auth_logout",
    )


def password_reset_rate_limit(request: Request):
    client_ip = get_client_ip(request)
    body = request.scope.get("_json")

    if isinstance(body, dict):
        email = str(body.get("email", "")).lower()
    else:
        email = ""

    email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
    key = f"rate_limit:password_reset:{client_ip}:{email_hash}"
    enforce_rate_limit_counter(
        key=key,
        limit=settings.password_reset_rate_limit_limit,
        window_seconds=settings.password_reset_rate_limit_window_seconds,
    )


def webhook_ingress_rate_limit():
    def dependency(request: Request):
        client_ip = get_client_ip(request)
        key = f"rate_limit:webhook_ingress:{client_ip}"
        enforce_rate_limit_counter(
            key=key,
            limit=settings.webhook_ingress_rate_limit_limit,
            window_seconds=settings.webhook_ingress_rate_limit_window_seconds,
        )

    return dependency


def enforce_webhook_provider_rate_limit(provider: str) -> None:
    normalized_provider = provider.strip().lower()

    if normalized_provider == "":
        return

    key = f"rate_limit:webhook_provider:{normalized_provider}"
    enforce_rate_limit_counter(
        key=key,
        limit=settings.webhook_provider_rate_limit_limit,
        window_seconds=settings.webhook_provider_rate_limit_window_seconds,
    )
