from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import Response
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

_TWIML = "application/xml"


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
        return Response(
            content=ivr_to_twiml(ivr_response, gather_action_url=gather_url, transfer_to=business.phone),
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


@router.post("/{business_id}/{session_id}", status_code=status.HTTP_200_OK)
async def twilio_voice_keypress(
    request: Request,
    business_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    digits: str = Form(default="", alias="Digits"),
):
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
    transfer_to = business.phone if business else None

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

    gather_url = _gather_url(business_id, session_id)
    return Response(
        content=ivr_to_twiml(ivr_response, gather_action_url=gather_url, transfer_to=transfer_to),
        media_type=_TWIML,
    )
