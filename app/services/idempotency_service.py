import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import BadRequestError, ConflictError
from app.core.redis import redis_client
from app.models.idempotency_record import IdempotencyRecord

logger = logging.getLogger("app.idempotency")

IDEMPOTENCY_LOCK_PREFIX = "idempotency:processing:"


def build_scope_key(scope: str, idempotency_key: str) -> str:
    normalized_key = idempotency_key.strip()

    if not normalized_key:
        raise BadRequestError("Idempotency-Key header is required")

    digest = hashlib.sha256(
        f"{scope}:{normalized_key}".encode("utf-8")
    ).hexdigest()

    return f"{scope}:{digest}"


def idempotency_lock_key(scope_key: str) -> str:
    return f"{IDEMPOTENCY_LOCK_PREFIX}{scope_key}"


def try_acquire_idempotency_lock(scope_key: str) -> bool:
    return (
        redis_client.set(
            idempotency_lock_key(scope_key),
            "1",
            nx=True,
            ex=settings.idempotency_processing_lock_ttl_seconds,
        )
        is True
    )


def release_idempotency_lock(scope_key: str) -> None:
    redis_client.delete(idempotency_lock_key(scope_key))


def get_cached_response(db: Session, scope_key: str) -> IdempotencyRecord | None:
    now = datetime.now(timezone.utc)

    return (
        db.query(IdempotencyRecord)
        .filter(
            IdempotencyRecord.scope_key == scope_key,
            IdempotencyRecord.expires_at > now,
        )
        .first()
    )


def store_response(
    db: Session,
    *,
    scope_key: str,
    status_code: int,
    response_body: dict,
) -> IdempotencyRecord:
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.idempotency_ttl_seconds
    )
    record = IdempotencyRecord(
        scope_key=scope_key,
        status_code=status_code,
        response_body=json.dumps(response_body),
        expires_at=expires_at,
    )

    db.add(record)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_record = get_cached_response(db, scope_key)

        if existing_record is None:
            raise

        return existing_record

    db.refresh(record)

    return record


def parse_cached_response_body(record: IdempotencyRecord) -> dict:
    return json.loads(record.response_body)


def cached_json_response(record: IdempotencyRecord):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=record.status_code,
        content=parse_cached_response_body(record),
    )


def begin_idempotent_request(db: Session, scope_key: str):
    cached_record = get_cached_response(db, scope_key)

    if cached_record is not None:
        return cached_record, False

    if not try_acquire_idempotency_lock(scope_key):
        cached_record = get_cached_response(db, scope_key)

        if cached_record is not None:
            return cached_record, False

        raise ConflictError("Duplicate request is already in progress")

    return None, True


def cleanup_expired_idempotency_records(db: Session) -> int:
    deleted_count = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.expires_at < datetime.now(timezone.utc))
        .delete(synchronize_session=False)
    )
    db.commit()

    logger.info("idempotency_expired_records_cleaned count=%s", deleted_count)

    return deleted_count
