from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.rate_limit import enforce_rate_limit_counter
from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.twilio_security import TwilioSignatureError, verify_twilio_signature
from app.db.session import get_db
from app.models.notification_outbox import NotificationOutbox, NotificationStatus
from app.services.business_service import get_business_global
from app.services.sms_reply_service import handle_sms_reply

router = APIRouter(prefix="/webhooks/twilio/sms", tags=["twilio-sms"])

_TWILIO_DELIVERED = "delivered"
_TWILIO_FAILED = {"failed", "undelivered"}


def _enforce_sms_status_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    enforce_rate_limit_counter(
        key=f"rate_limit:twilio_sms_status:{ip}",
        limit=settings.twilio_sms_status_rate_limit_limit,
        window_seconds=settings.twilio_sms_status_rate_limit_window_seconds,
    )


def _enforce_sms_inbound_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    enforce_rate_limit_counter(
        key=f"rate_limit:twilio_sms_inbound:{ip}",
        limit=settings.twilio_sms_inbound_rate_limit_limit,
        window_seconds=settings.twilio_sms_inbound_rate_limit_window_seconds,
    )


def _check_signature(request: Request, form_data: dict[str, str], signature: str | None) -> None:
    if not settings.twilio_auth_token:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature")
    try:
        verify_twilio_signature(
            url=str(request.url),
            form_data=form_data,
            signature=signature,
            auth_token=settings.twilio_auth_token,
        )
    except TwilioSignatureError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


@router.post("/status", status_code=status.HTTP_204_NO_CONTENT)
async def twilio_sms_status(
    request: Request,
    db: Session = Depends(get_db),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    sms_sid: str = Form(alias="SmsSid"),
    message_status: str = Form(alias="MessageStatus"),
):
    _enforce_sms_status_rate_limit(request)
    form_data = dict(await request.form())
    _check_signature(request, {k: str(v) for k, v in form_data.items()}, x_twilio_signature)

    notification = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.provider_message_id == sms_sid)
        .first()
    )
    if notification is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if notification.status == NotificationStatus.SENT and message_status in _TWILIO_FAILED:
        notification.status = NotificationStatus.FAILED
        notification.last_error = f"twilio_delivery_{message_status}"
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{business_id}/inbound", status_code=status.HTTP_204_NO_CONTENT)
async def twilio_sms_inbound(
    request: Request,
    business_id: int,
    db: Session = Depends(get_db),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    from_phone: str = Form(alias="From"),
    body: str = Form(default="", alias="Body"),
):
    _enforce_sms_inbound_rate_limit(request)
    form_data = dict(await request.form())
    _check_signature(request, {k: str(v) for k, v in form_data.items()}, x_twilio_signature)

    business = get_business_global(db, business_id)
    if business is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    handle_sms_reply(
        db,
        business_id=business_id,
        tenant_id=business.tenant_id,
        from_phone=from_phone,
        body=body,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
