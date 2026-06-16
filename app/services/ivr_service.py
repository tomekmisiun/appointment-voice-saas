import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.core.ivr import IvrAction, IvrOption, IvrResponse
from app.models.booking import BookingSource
from app.models.voice_session import IvrStep, VoiceSession
from app.services.availability_service import get_available_slots
from app.services.booking_service import create_booking
from app.services.business_service import require_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import list_services


def start_session(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    caller_phone: str,
) -> tuple[VoiceSession, IvrResponse]:
    require_business(db, business_id, tenant_id)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.ivr_session_ttl_minutes
    )
    session = VoiceSession(
        tenant_id=tenant_id,
        business_id=business_id,
        caller_phone=caller_phone,
        step=IvrStep.INCOMING,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, _main_menu_response(session.id)


def handle_keypress(
    db: Session,
    *,
    session_id: int,
    tenant_id: int,
    key: str,
) -> IvrResponse:
    session = (
        db.query(VoiceSession)
        .filter(VoiceSession.id == session_id, VoiceSession.tenant_id == tenant_id)
        .first()
    )
    if session is None:
        raise NotFoundError("Voice session not found")

    if datetime.now(tz=timezone.utc) >= session.expires_at:
        if session.step not in (IvrStep.BOOKING_CONFIRMED, IvrStep.NO_SLOTS,
                                IvrStep.EXPIRED, IvrStep.ABANDONED):
            session.step = IvrStep.EXPIRED
            db.commit()
        return IvrResponse(
            prompt="Your session has expired. Please call again to book an appointment.",
            action=IvrAction.END,
        )

    if session.step in (IvrStep.BOOKING_CONFIRMED, IvrStep.NO_SLOTS,
                        IvrStep.EXPIRED, IvrStep.ABANDONED):
        return IvrResponse(
            prompt="This session is already complete. Please call again.",
            action=IvrAction.END,
        )

    if session.step == IvrStep.INCOMING:
        return _handle_incoming(db, session, key)
    if session.step == IvrStep.SERVICE_SELECTION:
        return _handle_service_selection(db, session, key)
    if session.step == IvrStep.SLOT_SELECTION:
        return _handle_slot_selection(db, session, key)

    return IvrResponse(prompt="Unexpected session state.", action=IvrAction.END)


def expire_stale_sessions(db: Session) -> int:
    now = datetime.now(tz=timezone.utc)
    rows = (
        db.query(VoiceSession)
        .filter(
            VoiceSession.expires_at <= now,
            VoiceSession.step.not_in([
                IvrStep.BOOKING_CONFIRMED,
                IvrStep.NO_SLOTS,
                IvrStep.EXPIRED,
                IvrStep.ABANDONED,
            ]),
        )
        .all()
    )
    for row in rows:
        row.step = IvrStep.EXPIRED
    if rows:
        db.commit()
    return len(rows)


# --- step handlers ---

def _handle_incoming(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    if key == "1":
        services = list_services(db, session.business_id, session.tenant_id)
        if not services:
            session.step = IvrStep.NO_SLOTS
            db.commit()
            return IvrResponse(
                prompt="Sorry, no services are currently available. Please call back later.",
                action=IvrAction.END,
            )
        session.step = IvrStep.SERVICE_SELECTION
        db.commit()
        options = tuple(
            IvrOption(key=str(i + 1), label=svc.name)
            for i, svc in enumerate(services[:9])
        )
        prompt = "Please select a service: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if key == "2":
        session.step = IvrStep.ABANDONED
        db.commit()
        return IvrResponse(
            prompt="Transferring you to a staff member. Please hold.",
            action=IvrAction.TRANSFER,
        )

    return _main_menu_response(session.id)


def _handle_service_selection(
    db: Session, session: VoiceSession, key: str
) -> IvrResponse:
    services = list_services(db, session.business_id, session.tenant_id)
    if not services:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt="Sorry, no services are currently available. Please call back later.",
            action=IvrAction.END,
        )

    try:
        idx = int(key) - 1
        if idx < 0 or idx >= len(services[:9]):
            raise ValueError
    except ValueError:
        options = tuple(
            IvrOption(key=str(i + 1), label=svc.name)
            for i, svc in enumerate(services[:9])
        )
        prompt = "Invalid choice. Please select a service: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    selected_service = services[idx]
    slots = _find_slots(db, session=session, service_id=selected_service.id)

    if not slots:
        session.selected_service_id = selected_service.id
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=(
                f"Sorry, there are no available slots for {selected_service.name} "
                "in the next week. Please call back later."
            ),
            action=IvrAction.END,
        )

    session.selected_service_id = selected_service.id
    session.slot_candidates = json.dumps([
        {"start": s.isoformat(), "end": e.isoformat()}
        for s, e in slots
    ])
    session.step = IvrStep.SLOT_SELECTION
    db.commit()

    options = tuple(
        IvrOption(key=str(i + 1), label=_format_slot(s, e))
        for i, (s, e) in enumerate(slots)
    )
    prompt = f"Available slots for {selected_service.name}: " + ", ".join(
        f"press {o.key} for {o.label}" for o in options
    ) + ". Press your choice."
    return IvrResponse(prompt=prompt, options=options, session_id=session.id)


def _handle_slot_selection(
    db: Session, session: VoiceSession, key: str
) -> IvrResponse:
    raw = session.slot_candidates
    if not raw:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt="No slots are available. Please call back later.",
            action=IvrAction.END,
        )

    candidates: list[dict] = json.loads(raw)

    try:
        idx = int(key) - 1
        if idx < 0 or idx >= len(candidates):
            raise ValueError
    except ValueError:
        options = tuple(
            IvrOption(
                key=str(i + 1),
                label=_format_slot(
                    datetime.fromisoformat(c["start"]),
                    datetime.fromisoformat(c["end"]),
                ),
            )
            for i, c in enumerate(candidates)
        )
        prompt = "Invalid choice. Please select a slot: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    chosen = candidates[idx]
    starts_at = datetime.fromisoformat(chosen["start"])
    customer = get_or_create_customer(
        db,
        tenant_id=session.tenant_id,
        business_id=session.business_id,
        phone=session.caller_phone,
    )
    booking = create_booking(
        db,
        tenant_id=session.tenant_id,
        business_id=session.business_id,
        customer_id=customer.id,
        service_id=session.selected_service_id,
        staff_id=session.selected_staff_id,
        starts_at=starts_at,
        source=BookingSource.IVR,
    )
    session.booking_id = booking.id
    session.selected_slot_start = starts_at
    session.selected_slot_end = datetime.fromisoformat(chosen["end"])
    session.step = IvrStep.BOOKING_CONFIRMED
    db.commit()

    return IvrResponse(
        prompt=(
            f"Your appointment has been booked for {_format_slot(starts_at, session.selected_slot_end)}. "
            "You will receive an SMS confirmation. Thank you, goodbye!"
        ),
        action=IvrAction.END,
        session_id=session.id,
    )


# --- helpers ---

def _main_menu_response(session_id: int) -> IvrResponse:
    return IvrResponse(
        prompt="Welcome! Press 1 to book an appointment, or press 2 to speak with a staff member.",
        options=(
            IvrOption(key="1", label="Book an appointment"),
            IvrOption(key="2", label="Speak with staff"),
        ),
        session_id=session_id,
    )


def _find_slots(
    db: Session,
    *,
    session: VoiceSession,
    service_id: int,
) -> list[tuple[datetime, datetime]]:
    today = date.today()
    collected: list[tuple[datetime, datetime]] = []
    for i in range(settings.ivr_slot_search_days):
        day = today + timedelta(days=i)
        day_slots = get_available_slots(
            db,
            tenant_id=session.tenant_id,
            business_id=session.business_id,
            service_id=service_id,
            staff_id=None,
            query_date=day,
        )
        collected.extend(day_slots)
        if len(collected) >= settings.ivr_max_slots:
            break
    return collected[: settings.ivr_max_slots]


def _format_slot(starts_at: datetime, ends_at: datetime) -> str:
    return f"{starts_at.strftime('%A %B %-d at %-I:%M %p')} to {ends_at.strftime('%-I:%M %p')} UTC"
