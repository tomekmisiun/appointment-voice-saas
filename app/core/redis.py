import ssl
from datetime import datetime, timezone

from redis import Redis

from app.core.config import Settings, settings

REDIS_SSL_CERT_REQS = {
    "none": ssl.CERT_NONE,
    "optional": ssl.CERT_OPTIONAL,
    "required": ssl.CERT_REQUIRED,
}


def build_redis_client(app_settings: Settings) -> Redis:
    redis_kwargs = {
        "host": app_settings.redis_host,
        "port": app_settings.redis_port,
        "db": app_settings.redis_db,
        "decode_responses": True,
        "socket_timeout": app_settings.redis_socket_timeout_seconds,
        "socket_connect_timeout": app_settings.redis_socket_connect_timeout_seconds,
    }

    if app_settings.redis_username.strip():
        redis_kwargs["username"] = app_settings.redis_username

    if app_settings.redis_password.strip():
        redis_kwargs["password"] = app_settings.redis_password

    if app_settings.redis_ssl:
        redis_kwargs["ssl"] = True
        redis_kwargs["ssl_cert_reqs"] = REDIS_SSL_CERT_REQS[
            app_settings.redis_ssl_cert_reqs
        ]

    return Redis(**redis_kwargs)


redis_client = build_redis_client(settings)


def revoke_refresh_token(
    jti: str,
    expires_at: int,
    *,
    require_new: bool = False,
) -> bool:
    ttl_seconds = expires_at - int(datetime.now(timezone.utc).timestamp())

    if ttl_seconds <= 0:
        return not require_new

    key = f"revoked_refresh_token:{jti}"

    if require_new:
        return redis_client.set(key, "1", nx=True, ex=ttl_seconds) is True

    redis_client.set(key, "1", ex=ttl_seconds)
    return True


def is_refresh_token_revoked(jti: str) -> bool:
    return redis_client.exists(f"revoked_refresh_token:{jti}") == 1
