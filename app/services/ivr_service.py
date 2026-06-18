import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.core.ivr import IvrAction, IvrOption, IvrResponse
from app.models.booking import BookingSource
from app.models.business import BookingMode, TransferDestinationPolicy
from app.models.voice_session import IvrStep, VoiceSession
from app.models.working_hours import WorkingHours
from app.services.availability_service import get_available_slots
from app.services.booking_service import (
    cancel_booking,
    create_booking,
    get_next_confirmed_booking,
    require_booking,
    reschedule_booking,
)
from app.services.business_service import require_business
from app.services.client_service import get_client_by_customer_id
from app.services.customer_service import get_customer_by_phone, get_or_create_customer
from app.services.notification_service import (
    enqueue_external_booking_link_sms,
    enqueue_send_notification_job,
)
from app.services.service_service import list_services, require_service
from app.services.staff_service import get_eligible_transfer_staff, list_staff

logger = logging.getLogger(__name__)


def start_session(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    caller_phone: str,
) -> tuple[VoiceSession, IvrResponse]:
    business = require_business(db, business_id, tenant_id)
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
    greeting_name = _lookup_returning_caller_name(
        db, business_id=business_id, tenant_id=tenant_id, caller_phone=caller_phone
    )
    return session, _main_menu_response(
        session.id, business.booking_mode, greeting_name=greeting_name
    )


def _lookup_returning_caller_name(
    db: Session, *, business_id: int, tenant_id: int, caller_phone: str
) -> str | None:
    """Best-effort caller recognition for the welcome greeting. Matches the
    exact business_id+tenant_id+phone already enforced by
    get_customer_by_phone()/get_client_by_customer_id(), so this can never
    surface another caller's or another business's data. Prefers the
    richer Client profile name over the bare Customer name."""
    customer = get_customer_by_phone(
        db, business_id=business_id, tenant_id=tenant_id, phone=caller_phone
    )
    if customer is None:
        return None
    client = get_client_by_customer_id(
        db, business_id=business_id, tenant_id=tenant_id, customer_id=customer.id
    )
    if client is not None and client.name:
        return client.name
    return customer.name


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

    _TERMINAL_STEPS = (
        IvrStep.BOOKING_CONFIRMED,
        IvrStep.NO_SLOTS,
        IvrStep.EXPIRED,
        IvrStep.ABANDONED,
        IvrStep.EXTERNAL_LINK_SENT,
        IvrStep.BOOKING_CANCELLED,
    )

    if datetime.now(tz=timezone.utc) >= session.expires_at:
        if session.step not in _TERMINAL_STEPS:
            session.step = IvrStep.EXPIRED
            db.commit()
        return IvrResponse(
            prompt="Your session has expired. Please call again to book an appointment.",
            action=IvrAction.END,
        )

    if session.step in _TERMINAL_STEPS:
        return IvrResponse(
            prompt="This session is already complete. Please call again.",
            action=IvrAction.END,
        )

    if key == "":
        return _handle_no_input(db, session)

    # Reset consecutive-no-input counter on any non-empty keypress (valid or invalid).
    # Any key press proves the caller is still engaged; only silence should accumulate.
    if session.no_input_count:
        session.no_input_count = 0

    if key in _REPEAT_KEYS:
        db.commit()  # Persist no_input_count reset; repeat itself changes no other state.
        return _reprompt_for_no_input(db, session)

    if session.step == IvrStep.INCOMING:
        return _handle_incoming(db, session, key)
    if session.step == IvrStep.SERVICE_SELECTION:
        return _handle_service_selection(db, session, key)
    if session.step == IvrStep.STAFF_SELECTION:
        return _handle_staff_selection(db, session, key)
    if session.step == IvrStep.SLOT_SELECTION:
        return _handle_slot_selection(db, session, key)
    if session.step == IvrStep.TRANSFER_UNAVAILABLE:
        return _handle_transfer_unavailable(db, session, key)
    if session.step == IvrStep.MANAGE_BOOKING:
        return _handle_manage_booking(db, session, key)
    if session.step == IvrStep.RESCHEDULE_SLOT_SELECTION:
        return _handle_reschedule_slot_selection(db, session, key)

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
                IvrStep.EXTERNAL_LINK_SENT,
                IvrStep.BOOKING_CANCELLED,
            ]),
        )
        .all()
    )
    for row in rows:
        row.step = IvrStep.EXPIRED
    if rows:
        db.commit()
    return len(rows)


_NO_INPUT_MAX = 3
_INVALID_KEY_MAX = 5
# "*" replays the current prompt (standard DTMF convention). Digits are never
# repeat keys: menus can present up to 9 services/slots, so every digit 1-9 is
# a live selection and must reach the step handler.
_REPEAT_KEYS = frozenset({"*"})


def _handle_invalid_key(db: Session, session: VoiceSession, reprompt: IvrResponse) -> IvrResponse:
    """Increment invalid-key counter; terminate session after _INVALID_KEY_MAX total invalid keys."""
    session.invalid_key_count += 1
    if session.invalid_key_count >= _INVALID_KEY_MAX:
        session.step = IvrStep.EXPIRED
        db.commit()
        return IvrResponse(
            prompt=(
                "Too many invalid inputs. Your session has ended. "
                "Please call again to book an appointment."
            ),
            action=IvrAction.END,
        )
    db.commit()
    return reprompt


def _handle_no_input(db: Session, session: VoiceSession) -> IvrResponse:
    session.no_input_count += 1
    if session.no_input_count >= _NO_INPUT_MAX:
        session.step = IvrStep.EXPIRED
        db.commit()
        return IvrResponse(
            prompt=(
                "We didn't receive any input. Your session has ended. "
                "Please call again to book an appointment."
            ),
            action=IvrAction.END,
        )
    db.commit()
    reprompt = _reprompt_for_no_input(db, session)
    return IvrResponse(
        prompt="We didn't hear a response. " + reprompt.prompt,
        options=reprompt.options,
        action=reprompt.action,
        session_id=reprompt.session_id,
        transfer_destination=reprompt.transfer_destination,
    )


def _reprompt_for_no_input(db: Session, session: VoiceSession) -> IvrResponse:
    if session.step == IvrStep.INCOMING:
        business = require_business(db, session.business_id, session.tenant_id)
        return _main_menu_response(session.id, business.booking_mode)

    if session.step == IvrStep.SERVICE_SELECTION:
        services = list_services(db, session.business_id, session.tenant_id)
        options = tuple(
            IvrOption(key=str(i + 1), label=svc.name)
            for i, svc in enumerate(services[:9])
        )
        prompt = "Please select a service: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if session.step == IvrStep.STAFF_SELECTION:
        service = require_service(db, session.selected_service_id, session.tenant_id)
        staff_members = _schedulable_staff(db, session.business_id, session.tenant_id)
        return _staff_selection_response(session.id, staff_members, service.name)

    if session.step == IvrStep.SLOT_SELECTION:
        candidates: list[dict] = json.loads(session.slot_candidates or "[]")
        if not candidates:
            return IvrResponse(
                prompt="No slots are available. Please call back later.",
                action=IvrAction.END,
                session_id=session.id,
            )
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
        prompt = "Please select a slot: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if session.step == IvrStep.TRANSFER_UNAVAILABLE:
        return IvrResponse(
            prompt="Press 1 to go back to the main menu.",
            options=(IvrOption(key="1", label="Main menu"),),
            action=IvrAction.CONTINUE,
            session_id=session.id,
        )

    if session.step == IvrStep.MANAGE_BOOKING:
        booking = require_booking(db, session.managed_booking_id, session.tenant_id)
        return _manage_booking_response(db, session, booking)

    if session.step == IvrStep.RESCHEDULE_SLOT_SELECTION:
        candidates: list[dict] = json.loads(session.slot_candidates or "[]")
        if not candidates:
            return IvrResponse(
                prompt="No slots are available. Please call back later.",
                action=IvrAction.END,
                session_id=session.id,
            )
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
        prompt = "Please select a new time: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    return IvrResponse(
        prompt="Please make a selection.",
        action=IvrAction.CONTINUE,
        session_id=session.id,
    )


# --- step handlers ---

def _handle_incoming(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    if key == "1":
        business = require_business(db, session.business_id, session.tenant_id)
        if business.booking_mode == BookingMode.EXTERNAL_BOOKING_LINK:
            return _handle_press1_external(db, session, business)
        return _handle_press1_internal(db, session)

    if key == "2":
        return _handle_transfer_request(db, session)

    if key == "3":
        return _handle_manage_booking_request(db, session)

    business = require_business(db, session.business_id, session.tenant_id)
    return _handle_invalid_key(db, session, _main_menu_response(session.id, business.booking_mode))


def _handle_press1_internal(db: Session, session: VoiceSession) -> IvrResponse:
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


def _handle_press1_external(db: Session, session: VoiceSession, business) -> IvrResponse:
    url = business.external_booking_url or ""
    label = business.external_booking_label
    intent = enqueue_external_booking_link_sms(
        db,
        business=business,
        caller_phone=session.caller_phone,
        url=url,
        label=label,
    )
    session.step = IvrStep.EXTERNAL_LINK_SENT
    db.commit()
    enqueue_send_notification_job(intent.id)
    return IvrResponse(
        prompt=(
            "We have sent you an SMS with a link to book your appointment online. "
            "Thank you, goodbye!"
        ),
        action=IvrAction.END,
        session_id=session.id,
    )


def _handle_transfer_request(db: Session, session: VoiceSession) -> IvrResponse:
    business = require_business(db, session.business_id, session.tenant_id)

    if not business.transfer_enabled:
        session.step = IvrStep.TRANSFER_UNAVAILABLE
        db.commit()
        return IvrResponse(
            prompt="Transfer to staff is not available for this business. Press 1 to book an appointment.",
            action=IvrAction.CONTINUE,
            options=(IvrOption(key="1", label="Book an appointment"),),
            session_id=session.id,
        )

    destination = _resolve_transfer_destination(db, business, session.tenant_id)

    if destination is None:
        session.step = IvrStep.TRANSFER_UNAVAILABLE
        db.commit()
        return IvrResponse(
            prompt="Sorry, no staff members are available to take your call right now. Press 1 to book an appointment.",
            action=IvrAction.CONTINUE,
            options=(IvrOption(key="1", label="Book an appointment"),),
            session_id=session.id,
        )

    session.step = IvrStep.ABANDONED
    session.transfer_destination = destination
    db.commit()

    return IvrResponse(
        prompt="Transferring you to a staff member. Please hold.",
        action=IvrAction.TRANSFER,
        session_id=session.id,
        transfer_destination=destination,
    )


def _handle_transfer_unavailable(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    if key == "1":
        business = require_business(db, session.business_id, session.tenant_id)
        session.step = IvrStep.INCOMING
        db.commit()
        return _main_menu_response(session.id, business.booking_mode)
    reprompt = IvrResponse(
        prompt="Press 1 to go back to the main menu.",
        action=IvrAction.CONTINUE,
        options=(IvrOption(key="1", label="Main menu"),),
        session_id=session.id,
    )
    return _handle_invalid_key(db, session, reprompt)


def _handle_manage_booking_request(db: Session, session: VoiceSession) -> IvrResponse:
    customer = get_customer_by_phone(
        db,
        business_id=session.business_id,
        tenant_id=session.tenant_id,
        phone=session.caller_phone,
    )
    booking = (
        get_next_confirmed_booking(
            db,
            business_id=session.business_id,
            tenant_id=session.tenant_id,
            customer_id=customer.id,
        )
        if customer is not None
        else None
    )

    if booking is None:
        business = require_business(db, session.business_id, session.tenant_id)
        reprompt = _main_menu_response(session.id, business.booking_mode)
        return IvrResponse(
            prompt=(
                "We couldn't find an upcoming appointment for this number. "
                + reprompt.prompt
            ),
            options=reprompt.options,
            action=reprompt.action,
            session_id=reprompt.session_id,
        )

    session.managed_booking_id = booking.id
    session.step = IvrStep.MANAGE_BOOKING
    db.commit()
    return _manage_booking_response(db, session, booking)


def _manage_booking_response(db: Session, session: VoiceSession, booking) -> IvrResponse:
    service = require_service(db, booking.service_id, session.tenant_id)
    when = _format_slot(booking.starts_at, booking.ends_at)
    prompt = (
        f"We found your {service.name} appointment for {when}. "
        "Press 1 to cancel it, press 2 to reschedule it, or press 3 to go back to the main menu."
    )
    return IvrResponse(
        prompt=prompt,
        options=(
            IvrOption(key="1", label="Cancel appointment"),
            IvrOption(key="2", label="Reschedule appointment"),
            IvrOption(key="3", label="Main menu"),
        ),
        session_id=session.id,
    )


def _handle_manage_booking(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    booking = require_booking(db, session.managed_booking_id, session.tenant_id)

    if key == "1":
        cancel_booking(db, booking.id, session.tenant_id, reason="customer_ivr_cancel")
        session.step = IvrStep.BOOKING_CANCELLED
        db.commit()
        return IvrResponse(
            prompt="Your appointment has been cancelled. Thank you, goodbye!",
            action=IvrAction.END,
            session_id=session.id,
        )

    if key == "2":
        slots = _find_slots(db, session=session, service_id=booking.service_id)
        if not slots:
            session.step = IvrStep.NO_SLOTS
            db.commit()
            return IvrResponse(
                prompt="Sorry, there are no available slots to reschedule into right now. Please call back later.",
                action=IvrAction.END,
            )
        session.slot_candidates = json.dumps([
            {"start": s.isoformat(), "end": e.isoformat()}
            for s, e in slots
        ])
        session.step = IvrStep.RESCHEDULE_SLOT_SELECTION
        db.commit()
        options = tuple(
            IvrOption(key=str(i + 1), label=_format_slot(s, e))
            for i, (s, e) in enumerate(slots)
        )
        prompt = "Please select a new time: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if key == "3":
        business = require_business(db, session.business_id, session.tenant_id)
        session.step = IvrStep.INCOMING
        db.commit()
        return _main_menu_response(session.id, business.booking_mode)

    return _handle_invalid_key(db, session, _manage_booking_response(db, session, booking))


def _handle_reschedule_slot_selection(db: Session, session: VoiceSession, key: str) -> IvrResponse:
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
        prompt = "Invalid choice. Please select a new time: " + ", ".join(
            f"press {o.key} for {o.label}" for o in options
        ) + "."
        return _handle_invalid_key(
            db, session, IvrResponse(prompt=prompt, options=options, session_id=session.id)
        )

    chosen = candidates[idx]
    starts_at = datetime.fromisoformat(chosen["start"])

    new_booking = reschedule_booking(
        db,
        session.managed_booking_id,
        session.tenant_id,
        new_starts_at=starts_at,
        reason="customer_rescheduled_via_ivr",
        source=BookingSource.IVR,
    )

    session.booking_id = new_booking.id
    session.selected_slot_start = starts_at
    session.selected_slot_end = datetime.fromisoformat(chosen["end"])
    session.step = IvrStep.BOOKING_CONFIRMED
    db.commit()

    return IvrResponse(
        prompt=(
            f"Your appointment has been rescheduled to {_format_slot(starts_at, session.selected_slot_end)}. "
            "You will receive an SMS confirmation. Thank you, goodbye!"
        ),
        action=IvrAction.END,
        session_id=session.id,
    )


def _resolve_transfer_destination(db, business, tenant_id: int) -> str | None:
    policy = business.transfer_destination_policy
    if policy == TransferDestinationPolicy.BUSINESS_PHONE:
        phone = business.phone
        return phone if phone and phone.strip() else None
    if policy == TransferDestinationPolicy.STAFF:
        # First eligible staff by insertion order (id asc); intentional for determinism.
        eligible = get_eligible_transfer_staff(db, business.id, tenant_id)
        return eligible[0].phone if eligible else None
    logger.warning("Unknown transfer_destination_policy %r for business %d", policy, business.id)
    return None


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
        return _handle_invalid_key(
            db, session, IvrResponse(prompt=prompt, options=options, session_id=session.id)
        )

    selected_service = services[idx]
    session.selected_service_id = selected_service.id

    staff_members = _schedulable_staff(db, session.business_id, session.tenant_id)
    if len(staff_members) <= 1:
        # Nothing meaningful to choose between: auto-select the lone staff
        # member (if any) and skip straight to slot search.
        session.selected_staff_id = staff_members[0].id if staff_members else None
        return _proceed_to_slot_search(db, session, selected_service)

    session.step = IvrStep.STAFF_SELECTION
    db.commit()
    return _staff_selection_response(session.id, staff_members, selected_service.name)


def _handle_staff_selection(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    service = require_service(db, session.selected_service_id, session.tenant_id)
    staff_members = _schedulable_staff(db, session.business_id, session.tenant_id)

    if key == "0":
        session.selected_staff_id = None
        return _proceed_to_slot_search(db, session, service)

    try:
        idx = int(key) - 1
        if idx < 0 or idx >= len(staff_members[:9]):
            raise ValueError
    except ValueError:
        return _handle_invalid_key(
            db, session, _staff_selection_response(session.id, staff_members, service.name)
        )

    session.selected_staff_id = staff_members[idx].id
    return _proceed_to_slot_search(db, session, service)


def _staff_selection_response(
    session_id: int, staff_members: list, service_name: str
) -> IvrResponse:
    options = tuple(
        IvrOption(key=str(i + 1), label=member.name)
        for i, member in enumerate(staff_members[:9])
    ) + (IvrOption(key="0", label="Any available staff member"),)
    prompt = f"Who would you like to book your {service_name} with? " + ", ".join(
        f"press {o.key} for {o.label}" for o in options
    ) + "."
    return IvrResponse(prompt=prompt, options=options, session_id=session_id)


def _proceed_to_slot_search(db: Session, session: VoiceSession, selected_service) -> IvrResponse:
    slots = _find_slots(
        db, session=session, service_id=selected_service.id, staff_id=session.selected_staff_id
    )

    if not slots:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=(
                f"Sorry, there are no available slots for {selected_service.name} "
                "in the next week. Please call back later."
            ),
            action=IvrAction.END,
        )

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
        return _handle_invalid_key(
            db, session, IvrResponse(prompt=prompt, options=options, session_id=session.id)
        )

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

def _main_menu_response(
    session_id: int,
    booking_mode: str = BookingMode.INTERNAL_BOOKING,
    *,
    greeting_name: str | None = None,
) -> IvrResponse:
    if booking_mode == BookingMode.EXTERNAL_BOOKING_LINK:
        press1_label = "Receive a booking link by SMS"
        prompt = (
            "Welcome! Press 1 to receive a booking link by SMS, "
            "press 2 to speak with a staff member, "
            "or press 3 to manage an existing appointment."
        )
    else:
        press1_label = "Book an appointment"
        prompt = (
            "Welcome! Press 1 to book an appointment, "
            "press 2 to speak with a staff member, "
            "or press 3 to manage an existing appointment."
        )
    if greeting_name:
        prompt = f"Welcome back, {greeting_name}! " + prompt
    return IvrResponse(
        prompt=prompt,
        options=(
            IvrOption(key="1", label=press1_label),
            IvrOption(key="2", label="Speak with staff"),
            IvrOption(key="3", label="Manage an existing appointment"),
        ),
        session_id=session_id,
    )


def _schedulable_staff(db: Session, business_id: int, tenant_id: int) -> list:
    """Active staff who have at least one staff-specific working-hours row.

    get_available_slots() matches a given staff_id only against that staff
    member's own WorkingHours rows, with no fallback to business-level
    hours. Offering a staff member with no configured schedule in the IVR
    menu would therefore always dead-end in "no slots available", so they
    are excluded here rather than surfaced as a selectable option.
    """
    staff_members = list_staff(db, business_id, tenant_id)
    scheduled_ids = {
        row[0]
        for row in db.query(WorkingHours.staff_id)
        .filter(
            WorkingHours.business_id == business_id,
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.staff_id.isnot(None),
        )
        .distinct()
        .all()
    }
    return [s for s in staff_members if s.id in scheduled_ids]


def _find_slots(
    db: Session,
    *,
    session: VoiceSession,
    service_id: int,
    staff_id: int | None = None,
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
            staff_id=staff_id,
            query_date=day,
        )
        collected.extend(day_slots)
        if len(collected) >= settings.ivr_max_slots:
            break
    return collected[: settings.ivr_max_slots]


def _format_slot(starts_at: datetime, ends_at: datetime) -> str:
    return f"{starts_at.strftime('%A %B %-d at %-I:%M %p')} to {ends_at.strftime('%-I:%M %p')} UTC"
