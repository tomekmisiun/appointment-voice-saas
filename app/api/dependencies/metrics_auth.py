import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_metrics_access(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    if not settings.metrics_require_auth:
        return

    expected_token = settings.metrics_bearer_token.strip()

    if expected_token == "":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics authentication is not configured",
        )

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing metrics bearer token",
        )

    provided_token = authorization.removeprefix("Bearer ").strip()

    if not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid metrics bearer token",
        )
