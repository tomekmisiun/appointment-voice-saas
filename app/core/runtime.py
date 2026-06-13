from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings
from app.core.security_headers import SecurityHeadersMiddleware


def configure_runtime_middleware(app: FastAPI, settings: Settings) -> None:
    if settings.security_headers_enabled:
        app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_enabled=settings.hsts_enabled,
            hsts_max_age_seconds=settings.hsts_max_age_seconds,
        )

    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list(),
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_methods_list(),
            allow_headers=settings.cors_headers_list(),
        )

    if settings.trusted_hosts_enabled:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts_list(),
        )
