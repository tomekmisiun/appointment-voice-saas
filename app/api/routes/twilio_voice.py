import logging

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import Response
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies.rate_limit import enforce_rate_limit_counter
from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.core.twilio_security import TwilioSignatureError, verify_twilio_signature
from app.db.session import get_db
from app.models.voice_session import VoiceSession
from app.services.business_service import get_business_global
from app.services.ivr_service import handle_keypress, start_session
from app.services.twilio_voice_adapter import ivr_to_twiml

router = APIRouter(prefix="/webhooks/twilio/voice", tags=["twilio-voice"])
logger = logging.getLogger("app.twilio_voice")

_TWIML = "application/xml"
_BACKEND_UNAVAILABLE_TWIML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<Response><Say>We're experiencing technical difficulties. "
    "Please call back later. Goodbye.</Say><Hangup/></Response>"
)


def _backend_unavailable_response() -> Response:
    return Response(content=_BACKEND_UNAVAILABLE_TWIML, media_type=_TWIML)


def _enforce_voice_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    enforce_rate_limit_counter(
        key=f"rate_limit:twilio_voice:{ip}",
        limit=settings.twilio_voice_rate_limit_limit,
        window_seconds=settings.twilio_voice_rate_limit_window_seconds,
    )


def _check_signature(request: Request, form_data: dict[str, str], signature: str | None) -> None:
    if not settings.twilio_auth_token:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature")
    url = str(request.url)
    try:
        verify_twilio_signature(
            url=url,
            form_data=form_data,
            signature=signature,
            auth_token=settings.twilio_auth_token,
        )
    except TwilioSignatureError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


def _gather_url(business_id: int, session_id: int) -> str:
    base = settings.twilio_voice_base_url.rstrip("/")
    return f"{base}/api/v1/webhooks/twilio/voice/{business_id}/{session_id}"


@router.post("/{business_id}", status_code=status.HTTP_200_OK)
async def twilio_voice_inbound(
    request: Request,
    business_id: int,
    db: Session = Depends(get_db),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    call_sid: str = Form(alias="CallSid"),
    caller: str = Form(default="", alias="From"),
):
    try:
        _enforce_voice_rate_limit(request)
        form_data = dict(await request.form())
        _check_signature(request, {k: str(v) for k, v in form_data.items()}, x_twilio_signature)

        business = get_business_global(db, business_id)
        if business is None:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response><Say>Sorry, this number is not configured. Goodbye.</Say><Hangup/></Response>"
            )
            return Response(content=twiml, media_type=_TWIML)

        existing = db.query(VoiceSession).filter(VoiceSession.call_sid == call_sid).first()
        if existing is not None:
            ivr_response = handle_keypress(
                db, session_id=existing.id, tenant_id=existing.tenant_id, key=""
            )
            gather_url = _gather_url(business_id, existing.id)
            transfer_to = ivr_response.transfer_destination or business.phone
            return Response(
                content=ivr_to_twiml(ivr_response, gather_action_url=gather_url, transfer_to=transfer_to),
                media_type=_TWIML,
            )

        try:
            session, ivr_response = start_session(
                db,
                business_id=business_id,
                tenant_id=business.tenant_id,
                caller_phone=caller or "unknown",
            )
        except NotFoundError:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response><Say>Sorry, this number is not configured. Goodbye.</Say><Hangup/></Response>"
            )
            return Response(content=twiml, media_type=_TWIML)

        session.call_sid = call_sid
        db.commit()

        gather_url = _gather_url(business_id, session.id)
        return Response(
            content=ivr_to_twiml(ivr_response, gather_action_url=gather_url, transfer_to=business.phone),
            media_type=_TWIML,
        )
    except (OperationalError, RedisError):
        logger.exception("twilio_voice_backend_unavailable business_id=%s", business_id)
        return _backend_unavailable_response()
    except HTTPException as exc:
        # enforce_rate_limit_counter() already converts a RedisError into an
        # HTTPException(503) itself; treat that the same as a raw RedisError.
        # Any other HTTPException (403 bad signature, 429 rate limited) is a
        # real decision, not an outage — let it propagate as-is.
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.exception("twilio_voice_backend_unavailable business_id=%s", business_id)
            return _backend_unavailable_response()
        raise


@router.post("/{business_id}/{session_id}", status_code=status.HTTP_200_OK)
async def twilio_voice_keypress(
    request: Request,
    business_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    digits: str = Form(default="", alias="Digits"),
):
    try:
        _enforce_voice_rate_limit(request)
        form_data = dict(await request.form())
        _check_signature(request, {k: str(v) for k, v in form_data.items()}, x_twilio_signature)

        session = db.query(VoiceSession).filter(VoiceSession.id == session_id).first()
        if session is None:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response><Say>Session not found. Please call again.</Say><Hangup/></Response>"
            )
            return Response(content=twiml, media_type=_TWIML)

        business = get_business_global(db, business_id)

        try:
            ivr_response = handle_keypress(
                db, session_id=session_id, tenant_id=session.tenant_id, key=digits
            )
        except NotFoundError:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response><Say>Session not found. Please call again.</Say><Hangup/></Response>"
            )
            return Response(content=twiml, media_type=_TWIML)

        # Prefer the IVR-resolved destination (respects STAFF policy); fall back to business phone.
        transfer_to = ivr_response.transfer_destination or (business.phone if business else None)
        gather_url = _gather_url(business_id, session_id)
        return Response(
            content=ivr_to_twiml(ivr_response, gather_action_url=gather_url, transfer_to=transfer_to),
            media_type=_TWIML,
        )
    except (OperationalError, RedisError):
        logger.exception("twilio_voice_backend_unavailable business_id=%s session_id=%s", business_id, session_id)
        return _backend_unavailable_response()
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.exception(
                "twilio_voice_backend_unavailable business_id=%s session_id=%s", business_id, session_id
            )
            return _backend_unavailable_response()
        raise
