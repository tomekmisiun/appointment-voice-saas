import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.core.ivr import IvrAction, IvrOption, IvrResponse
from app.core.ivr_prompts import (
    IVR_DEFAULT_LOCALE,
    PromptKey,
    format_option_list,
    resolve_prompt,
)
from app.models.booking import BookingSource
from app.models.business import BookingMode, TransferDestinationPolicy
from app.models.voice_session import IvrStep, VoiceSession
from app.models.working_hours import WorkingHours
from app.services.availability_service import get_available_slots
from app.services.booking_service import (
    cancel_booking,
    create_booking,
    get_last_staff_booking,
    get_next_confirmed_booking,
    require_booking_in_business,
    reschedule_booking,
)
from app.services.business_service import require_business
from app.services.client_service import get_client_by_customer_id
from app.services.customer_service import get_customer_by_phone, get_or_create_customer
from app.services.notification_service import (
    enqueue_external_booking_link_sms,
    enqueue_send_notification_job,
)
from app.services.service_service import list_services, require_service_in_business
from app.services.staff_service import get_eligible_transfer_staff, list_staff

logger = logging.getLogger(__name__)


def _session_locale(session: VoiceSession) -> str:
    """Single extension point for P3-009: every prompt call site resolves
    its locale through here rather than hardcoding IVR_DEFAULT_LOCALE, so
    wiring up a real per-session/per-business locale later (e.g. a
    VoiceSession.locale column) only means changing this one function."""
    return IVR_DEFAULT_LOCALE


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
        session.id,
        business.booking_mode,
        greeting_name=greeting_name,
        locale=_session_locale(session),
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
            prompt=resolve_prompt(PromptKey.SESSION_EXPIRED, locale=_session_locale(session)),
            action=IvrAction.END,
        )

    if session.step in _TERMINAL_STEPS:
        return IvrResponse(
            prompt=resolve_prompt(
                PromptKey.SESSION_ALREADY_COMPLETE, locale=_session_locale(session)
            ),
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

    return IvrResponse(
        prompt=resolve_prompt(PromptKey.UNEXPECTED_STATE, locale=_session_locale(session)),
        action=IvrAction.END,
    )


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
            prompt=resolve_prompt(
                PromptKey.TOO_MANY_INVALID_KEYS, locale=_session_locale(session)
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
            prompt=resolve_prompt(PromptKey.TOO_MANY_NO_INPUT, locale=_session_locale(session)),
            action=IvrAction.END,
        )
    db.commit()
    reprompt = _reprompt_for_no_input(db, session)
    return IvrResponse(
        prompt=resolve_prompt(PromptKey.NO_INPUT_PREFIX, locale=_session_locale(session))
        + reprompt.prompt,
        options=reprompt.options,
        action=reprompt.action,
        session_id=reprompt.session_id,
        transfer_destination=reprompt.transfer_destination,
    )


def _reprompt_for_no_input(db: Session, session: VoiceSession) -> IvrResponse:
    if session.step == IvrStep.INCOMING:
        business = require_business(db, session.business_id, session.tenant_id)
        return _main_menu_response(session.id, business.booking_mode, locale=_session_locale(session))

    if session.step == IvrStep.SERVICE_SELECTION:
        services = list_services(db, session.business_id, session.tenant_id)
        options = tuple(
            IvrOption(key=str(i + 1), label=svc.name)
            for i, svc in enumerate(services[:9])
        )
        loc = _session_locale(session)
        prompt = resolve_prompt(
            PromptKey.SELECT_SERVICE, locale=loc, options=format_option_list(options, locale=loc)
        )
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if session.step == IvrStep.STAFF_SELECTION:
        service = require_service_in_business(
            db, session.selected_service_id, session.business_id, session.tenant_id
        )
        staff_members = _schedulable_staff(db, session.business_id, session.tenant_id)
        staff_members, preferred_staff_id = _reorder_preferred_staff(db, session, staff_members)
        return _staff_selection_response(
            session.id,
            staff_members,
            service.name,
            preferred_staff_id=preferred_staff_id,
            locale=_session_locale(session),
        )

    if session.step == IvrStep.SLOT_SELECTION:
        candidates: list[dict] = json.loads(session.slot_candidates or "[]")
        loc = _session_locale(session)
        if not candidates:
            return IvrResponse(
                prompt=resolve_prompt(PromptKey.NO_SLOTS, locale=loc),
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
        prompt = resolve_prompt(
            PromptKey.SELECT_SLOT, locale=loc, options=format_option_list(options, locale=loc)
        )
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if session.step == IvrStep.TRANSFER_UNAVAILABLE:
        loc = _session_locale(session)
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.PRESS_1_MAIN_MENU, locale=loc),
            options=(IvrOption(key="1", label=resolve_prompt(PromptKey.LABEL_MAIN_MENU, locale=loc)),),
            action=IvrAction.CONTINUE,
            session_id=session.id,
        )

    if session.step == IvrStep.MANAGE_BOOKING:
        booking = require_booking_in_business(
            db, session.managed_booking_id, session.business_id, session.tenant_id
        )
        return _manage_booking_response(db, session, booking)

    if session.step == IvrStep.RESCHEDULE_SLOT_SELECTION:
        candidates: list[dict] = json.loads(session.slot_candidates or "[]")
        loc = _session_locale(session)
        if not candidates:
            return IvrResponse(
                prompt=resolve_prompt(PromptKey.NO_SLOTS, locale=loc),
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
        prompt = resolve_prompt(
            PromptKey.SELECT_NEW_TIME, locale=loc, options=format_option_list(options, locale=loc)
        )
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    return IvrResponse(
        prompt=resolve_prompt(PromptKey.PLEASE_MAKE_A_SELECTION, locale=_session_locale(session)),
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
    return _handle_invalid_key(db, session, _main_menu_response(session.id, business.booking_mode, locale=_session_locale(session)))


def _handle_press1_internal(db: Session, session: VoiceSession) -> IvrResponse:
    services = list_services(db, session.business_id, session.tenant_id)
    loc = _session_locale(session)
    if not services:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.NO_SERVICES, locale=loc),
            action=IvrAction.END,
        )
    session.step = IvrStep.SERVICE_SELECTION
    db.commit()
    options = tuple(
        IvrOption(key=str(i + 1), label=svc.name)
        for i, svc in enumerate(services[:9])
    )
    prompt = resolve_prompt(
        PromptKey.SELECT_SERVICE, locale=loc, options=format_option_list(options, locale=loc)
    )
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
        prompt=resolve_prompt(PromptKey.EXTERNAL_LINK_SENT, locale=_session_locale(session)),
        action=IvrAction.END,
        session_id=session.id,
    )


def _handle_transfer_request(db: Session, session: VoiceSession) -> IvrResponse:
    business = require_business(db, session.business_id, session.tenant_id)
    loc = _session_locale(session)

    if not business.transfer_enabled:
        session.step = IvrStep.TRANSFER_UNAVAILABLE
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.TRANSFER_DISABLED, locale=loc),
            action=IvrAction.CONTINUE,
            options=(IvrOption(key="1", label=resolve_prompt(PromptKey.LABEL_BOOK_APPOINTMENT, locale=loc)),),
            session_id=session.id,
        )

    destination = _resolve_transfer_destination(db, business, session.tenant_id)

    if destination is None:
        session.step = IvrStep.TRANSFER_UNAVAILABLE
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.TRANSFER_NO_STAFF, locale=loc),
            action=IvrAction.CONTINUE,
            options=(IvrOption(key="1", label=resolve_prompt(PromptKey.LABEL_BOOK_APPOINTMENT, locale=loc)),),
            session_id=session.id,
        )

    session.step = IvrStep.ABANDONED
    session.transfer_destination = destination
    db.commit()

    return IvrResponse(
        prompt=resolve_prompt(PromptKey.TRANSFERRING, locale=loc),
        action=IvrAction.TRANSFER,
        session_id=session.id,
        transfer_destination=destination,
    )


def _handle_transfer_unavailable(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    if key == "1":
        business = require_business(db, session.business_id, session.tenant_id)
        session.step = IvrStep.INCOMING
        db.commit()
        return _main_menu_response(session.id, business.booking_mode, locale=_session_locale(session))
    loc = _session_locale(session)
    reprompt = IvrResponse(
        prompt=resolve_prompt(PromptKey.PRESS_1_MAIN_MENU, locale=loc),
        action=IvrAction.CONTINUE,
        options=(IvrOption(key="1", label=resolve_prompt(PromptKey.LABEL_MAIN_MENU, locale=loc)),),
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
        reprompt = _main_menu_response(session.id, business.booking_mode, locale=_session_locale(session))
        return IvrResponse(
            prompt=resolve_prompt(
                PromptKey.NO_UPCOMING_BOOKING_PREFIX, locale=_session_locale(session)
            )
            + reprompt.prompt,
            options=reprompt.options,
            action=reprompt.action,
            session_id=reprompt.session_id,
        )

    session.managed_booking_id = booking.id
    session.step = IvrStep.MANAGE_BOOKING
    db.commit()
    return _manage_booking_response(db, session, booking)


def _manage_booking_response(db: Session, session: VoiceSession, booking) -> IvrResponse:
    service = require_service_in_business(
        db, booking.service_id, session.business_id, session.tenant_id
    )
    loc = _session_locale(session)
    when = _format_slot(booking.starts_at, booking.ends_at)
    prompt = resolve_prompt(
        PromptKey.MANAGE_BOOKING_FOUND, locale=loc, service_name=service.name, when=when
    )
    return IvrResponse(
        prompt=prompt,
        options=(
            IvrOption(key="1", label=resolve_prompt(PromptKey.LABEL_CANCEL_APPOINTMENT, locale=loc)),
            IvrOption(key="2", label=resolve_prompt(PromptKey.LABEL_RESCHEDULE_APPOINTMENT, locale=loc)),
            IvrOption(key="3", label=resolve_prompt(PromptKey.LABEL_MAIN_MENU, locale=loc)),
        ),
        session_id=session.id,
    )


def _handle_manage_booking(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    booking = require_booking_in_business(
        db, session.managed_booking_id, session.business_id, session.tenant_id
    )

    loc = _session_locale(session)

    if key == "1":
        cancel_booking(
            db, booking.id, session.business_id, session.tenant_id, reason="customer_ivr_cancel"
        )
        session.step = IvrStep.BOOKING_CANCELLED
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.BOOKING_CANCELLED, locale=loc),
            action=IvrAction.END,
            session_id=session.id,
        )

    if key == "2":
        slots = _find_slots(db, session=session, service_id=booking.service_id)
        if not slots:
            session.step = IvrStep.NO_SLOTS
            db.commit()
            return IvrResponse(
                prompt=resolve_prompt(PromptKey.NO_SLOTS_TO_RESCHEDULE, locale=loc),
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
        prompt = resolve_prompt(
            PromptKey.SELECT_NEW_TIME, locale=loc, options=format_option_list(options, locale=loc)
        )
        return IvrResponse(prompt=prompt, options=options, session_id=session.id)

    if key == "3":
        business = require_business(db, session.business_id, session.tenant_id)
        session.step = IvrStep.INCOMING
        db.commit()
        return _main_menu_response(session.id, business.booking_mode, locale=_session_locale(session))

    return _handle_invalid_key(db, session, _manage_booking_response(db, session, booking))


def _handle_reschedule_slot_selection(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    raw = session.slot_candidates
    loc = _session_locale(session)
    if not raw:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.NO_SLOTS, locale=loc),
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
        prompt = resolve_prompt(
            PromptKey.INVALID_SELECT_NEW_TIME,
            locale=loc,
            options=format_option_list(options, locale=loc),
        )
        return _handle_invalid_key(
            db, session, IvrResponse(prompt=prompt, options=options, session_id=session.id)
        )

    chosen = candidates[idx]
    starts_at = datetime.fromisoformat(chosen["start"])

    new_booking = reschedule_booking(
        db,
        session.managed_booking_id,
        session.business_id,
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
        prompt=resolve_prompt(
            PromptKey.BOOKING_RESCHEDULED,
            locale=_session_locale(session),
            when=_format_slot(starts_at, session.selected_slot_end),
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
    loc = _session_locale(session)
    if not services:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.NO_SERVICES, locale=loc),
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
        prompt = resolve_prompt(
            PromptKey.INVALID_SELECT_SERVICE,
            locale=loc,
            options=format_option_list(options, locale=loc),
        )
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

    staff_members, preferred_staff_id = _reorder_preferred_staff(db, session, staff_members)
    session.step = IvrStep.STAFF_SELECTION
    db.commit()
    return _staff_selection_response(
        session.id,
        staff_members,
        selected_service.name,
        preferred_staff_id=preferred_staff_id,
        locale=_session_locale(session),
    )


def _handle_staff_selection(db: Session, session: VoiceSession, key: str) -> IvrResponse:
    service = require_service_in_business(
        db, session.selected_service_id, session.business_id, session.tenant_id
    )
    staff_members = _schedulable_staff(db, session.business_id, session.tenant_id)
    staff_members, preferred_staff_id = _reorder_preferred_staff(db, session, staff_members)

    if key == "0":
        session.selected_staff_id = None
        return _proceed_to_slot_search(db, session, service)

    try:
        idx = int(key) - 1
        if idx < 0 or idx >= len(staff_members[:9]):
            raise ValueError
    except ValueError:
        return _handle_invalid_key(
            db,
            session,
            _staff_selection_response(
                session.id,
                staff_members,
                service.name,
                preferred_staff_id=preferred_staff_id,
                locale=_session_locale(session),
            ),
        )

    session.selected_staff_id = staff_members[idx].id
    return _proceed_to_slot_search(db, session, service)


def _last_used_staff_id(db: Session, session: VoiceSession) -> int | None:
    """staff_id from the caller's most recent past booking with this
    business, used to fast-path the staff-selection menu (P2-007). Matches
    the caller phone to a Customer the same way the returning-caller
    greeting does (P2-003), so it never crosses business/tenant boundaries."""
    customer = get_customer_by_phone(
        db,
        business_id=session.business_id,
        tenant_id=session.tenant_id,
        phone=session.caller_phone,
    )
    if customer is None:
        return None
    last_booking = get_last_staff_booking(
        db,
        business_id=session.business_id,
        tenant_id=session.tenant_id,
        customer_id=customer.id,
    )
    return last_booking.staff_id if last_booking is not None else None


def _reorder_preferred_staff(
    db: Session, session: VoiceSession, staff_members: list
) -> tuple[list, int | None]:
    """Move the caller's last-used staff member (if still active and
    schedulable) to the front of the menu so it's offered as option 1."""
    preferred_id = _last_used_staff_id(db, session)
    if preferred_id is None:
        return staff_members, None
    preferred = [s for s in staff_members if s.id == preferred_id]
    if not preferred:
        return staff_members, None
    others = [s for s in staff_members if s.id != preferred_id]
    return preferred + others, preferred_id


def _staff_selection_response(
    session_id: int,
    staff_members: list,
    service_name: str,
    *,
    preferred_staff_id: int | None = None,
    locale: str = IVR_DEFAULT_LOCALE,
) -> IvrResponse:
    options = tuple(
        IvrOption(key=str(i + 1), label=member.name)
        for i, member in enumerate(staff_members[:9])
    ) + (IvrOption(key="0", label=resolve_prompt(PromptKey.LABEL_ANY_AVAILABLE_STAFF, locale=locale)),)

    parts = []
    for i, member in enumerate(staff_members[:9]):
        key = str(i + 1)
        if preferred_staff_id is not None and member.id == preferred_staff_id:
            parts.append(
                resolve_prompt(
                    PromptKey.STAFF_OPTION_PREFERRED, locale=locale, key=key, label=member.name
                )
            )
        else:
            parts.append(
                resolve_prompt(PromptKey.OPTION_ITEM, locale=locale, key=key, label=member.name)
            )
    parts.append(resolve_prompt(PromptKey.STAFF_OPTION_ANY, locale=locale))

    prompt = resolve_prompt(
        PromptKey.STAFF_SELECTION_PROMPT,
        locale=locale,
        service_name=service_name,
        options=", ".join(parts),
    )
    return IvrResponse(prompt=prompt, options=options, session_id=session_id)


def _proceed_to_slot_search(db: Session, session: VoiceSession, selected_service) -> IvrResponse:
    slots = _find_slots(
        db, session=session, service_id=selected_service.id, staff_id=session.selected_staff_id
    )
    loc = _session_locale(session)

    if not slots:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(
                PromptKey.NO_SLOTS_FOR_SERVICE, locale=loc, service_name=selected_service.name
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
    prompt = resolve_prompt(
        PromptKey.AVAILABLE_SLOTS_FOR_SERVICE,
        locale=loc,
        service_name=selected_service.name,
        options=format_option_list(options, locale=loc),
    )
    return IvrResponse(prompt=prompt, options=options, session_id=session.id)


def _handle_slot_selection(
    db: Session, session: VoiceSession, key: str
) -> IvrResponse:
    raw = session.slot_candidates
    if not raw:
        session.step = IvrStep.NO_SLOTS
        db.commit()
        return IvrResponse(
            prompt=resolve_prompt(PromptKey.NO_SLOTS, locale=_session_locale(session)),
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
        loc = _session_locale(session)
        prompt = resolve_prompt(
            PromptKey.INVALID_SELECT_SLOT, locale=loc, options=format_option_list(options, locale=loc)
        )
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
        prompt=resolve_prompt(
            PromptKey.BOOKING_CONFIRMED,
            locale=_session_locale(session),
            when=_format_slot(starts_at, session.selected_slot_end),
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
    locale: str = IVR_DEFAULT_LOCALE,
) -> IvrResponse:
    if booking_mode == BookingMode.EXTERNAL_BOOKING_LINK:
        press1_label = resolve_prompt(PromptKey.LABEL_BOOKING_LINK_SMS, locale=locale)
        prompt = resolve_prompt(PromptKey.MAIN_MENU_EXTERNAL, locale=locale)
    else:
        press1_label = resolve_prompt(PromptKey.LABEL_BOOK_APPOINTMENT, locale=locale)
        prompt = resolve_prompt(PromptKey.MAIN_MENU_INTERNAL, locale=locale)
    if greeting_name:
        prompt = (
            resolve_prompt(PromptKey.GREETING_PREFIX, locale=locale, name=greeting_name) + prompt
        )
    return IvrResponse(
        prompt=prompt,
        options=(
            IvrOption(key="1", label=press1_label),
            IvrOption(key="2", label=resolve_prompt(PromptKey.LABEL_SPEAK_WITH_STAFF, locale=locale)),
            IvrOption(key="3", label=resolve_prompt(PromptKey.LABEL_MANAGE_BOOKING, locale=locale)),
        ),
        session_id=session_id,
    )


def _schedulable_staff(db: Session, business_id: int, tenant_id: int) -> list:
    """Active staff who can plausibly be offered a real availability
    search.

    Since P3-002, `get_available_slots()` falls back to the business's
    own (staff_id IS NULL) WorkingHours rows for any staff member with no
    staff-specific override -- so a staff member is only ever a guaranteed,
    permanent dead-end ("no slots available" on every date, not just a
    fully-booked one) if *neither* they nor the business has any working
    hours configured at all. If the business has any business-wide hours,
    every active staff member is schedulable through that fallback; only
    when the business has none does staff-specific hours become the sole
    determinant, matching the pre-P3-002 behavior in that edge case.
    """
    staff_members = list_staff(db, business_id, tenant_id)

    business_has_hours = (
        db.query(WorkingHours.id)
        .filter(
            WorkingHours.business_id == business_id,
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.staff_id.is_(None),
        )
        .first()
        is not None
    )
    if business_has_hours:
        return staff_members

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
