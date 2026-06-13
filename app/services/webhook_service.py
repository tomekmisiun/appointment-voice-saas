import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import ConflictError, PayloadTooLargeError, UnauthorizedError
from app.core.webhook_security import (
    WebhookSignatureError,
    hash_payload,
    verify_timestamped_hmac_signature,
)
from app.models.webhook_event import WebhookEvent

logger = logging.getLogger("app.webhooks")


def enforce_webhook_body_size(raw_body: bytes) -> None:
    if len(raw_body) > settings.webhook_max_body_bytes:
        raise PayloadTooLargeError("Webhook payload too large")


def persist_webhook_event(
    db: Session,
    *,
    provider: str,
    event_id: str,
    payload: bytes,
) -> WebhookEvent:
    event = WebhookEvent(
        provider=provider,
        event_id=event_id,
        payload_hash=hash_payload(payload),
    )

    db.add(event)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Webhook event already processed")

    db.refresh(event)

    return event


def cleanup_old_webhook_events(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.webhook_event_retention_days,
    )
    deleted_count = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.received_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()

    logger.info("webhook_events_cleaned count=%s cutoff=%s", deleted_count, cutoff.isoformat())

    return deleted_count


def verify_inbound_webhook_signature(
    *,
    payload: bytes,
    signature: str | None,
    timestamp: str | None,
    secret: str,
    tolerance_seconds: int,
) -> None:
    if signature is None:
        raise UnauthorizedError("Webhook signature header is required")

    parsed_timestamp: int | None = None

    if timestamp is not None:
        try:
            parsed_timestamp = int(timestamp.strip())
        except ValueError as exc:
            raise UnauthorizedError(
                "Webhook timestamp must be a Unix timestamp",
            ) from exc

    try:
        verify_timestamped_hmac_signature(
            payload=payload,
            signature=signature,
            timestamp=parsed_timestamp,
            secret=secret,
            tolerance_seconds=tolerance_seconds,
        )
    except WebhookSignatureError as exc:
        raise UnauthorizedError(str(exc)) from exc
