from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies.idempotency import get_idempotency_key
from app.api.dependencies.rate_limit import (
    enforce_webhook_provider_rate_limit,
    webhook_ingress_rate_limit,
)
from app.api.openapi import AUTH_ERROR_RESPONSES
from app.core.config import settings
from app.core.domain_errors import ConflictError
from app.db.session import get_db
from app.schemas.webhook import WebhookInboundRequest, WebhookInboundResponse
from app.services.idempotency_service import (
    begin_idempotent_request,
    build_scope_key,
    cached_json_response,
    parse_cached_response_body,
    release_idempotency_lock,
    store_response,
)
from app.services.webhook_service import (
    enforce_webhook_body_size,
    persist_webhook_event,
    verify_inbound_webhook_signature,
)


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/inbound",
    response_model=WebhookInboundResponse,
    summary="Receive a signed inbound webhook",
    description=(
        "Provider-neutral webhook entrypoint with timestamped HMAC signature "
        "verification, replay-window protection, event deduplication, and "
        "Idempotency-Key replay-safe response caching."
    ),
    responses=AUTH_ERROR_RESPONSES,
)
async def inbound_webhook(
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(get_idempotency_key),
    _: None = Depends(webhook_ingress_rate_limit()),
    signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    timestamp: str | None = Header(default=None, alias="X-Webhook-Timestamp"),
):
    raw_body = await request.body()
    enforce_webhook_body_size(raw_body)
    scope_key = build_scope_key("webhooks:inbound", idempotency_key)
    cached_record, lock_acquired = begin_idempotent_request(db, scope_key)

    if cached_record is not None:
        return cached_json_response(cached_record)

    try:
        verify_inbound_webhook_signature(
            payload=raw_body,
            signature=signature,
            timestamp=timestamp,
            secret=settings.webhook_signature_secret,
            tolerance_seconds=settings.webhook_signature_tolerance_seconds,
        )

        payload = WebhookInboundRequest.model_validate_json(raw_body)
        enforce_webhook_provider_rate_limit(payload.provider)

        try:
            persist_webhook_event(
                db,
                provider=payload.provider,
                event_id=payload.event_id,
                payload=raw_body,
            )
        except ConflictError:
            response_body = {
                "status": "duplicate",
                "provider": payload.provider,
                "event_id": payload.event_id,
            }
            stored_record = store_response(
                db,
                scope_key=scope_key,
                status_code=status.HTTP_409_CONFLICT,
                response_body=response_body,
            )
            return JSONResponse(
                status_code=stored_record.status_code,
                content=parse_cached_response_body(stored_record),
            )

        response_body = {
            "status": "accepted",
            "provider": payload.provider,
            "event_id": payload.event_id,
        }
        stored_record = store_response(
            db,
            scope_key=scope_key,
            status_code=status.HTTP_200_OK,
            response_body=response_body,
        )

        return parse_cached_response_body(stored_record)
    finally:
        if lock_acquired:
            release_idempotency_lock(scope_key)
