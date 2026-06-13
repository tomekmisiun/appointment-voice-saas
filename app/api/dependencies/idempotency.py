from fastapi import Header, HTTPException, status


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str:
    normalized_key = idempotency_key.strip() if idempotency_key else ""

    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    return normalized_key
