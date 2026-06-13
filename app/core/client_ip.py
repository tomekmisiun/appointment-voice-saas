from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    if settings.rate_limit_trust_forwarded_headers:
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")

        if real_ip:
            return real_ip.strip()

    if request.client is None:
        return "unknown"

    return request.client.host
