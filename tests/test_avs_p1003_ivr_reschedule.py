"""P1-003: IVR self-service reschedule/cancel for an existing booking.

Pressing "3" at the main menu looks up the caller's soonest upcoming
confirmed booking by caller ID. From there the caller can cancel it,
reschedule it (same service/staff, new time), or go back to the main menu.
Reschedule is cancel-old + create-new, reusing cancel_booking()/
create_booking() so audit/notification/calendar side effects stay correct.
"""
from datetime import datetime, time, timedelta, timezone

from app.core.ivr import IvrAction
from app.models.booking import BookingStatus
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.working_hours_service import create_working_hours


def _setup(db, *, full_day: bool = True):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reschedule Salon", timezone="UTC")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30)
    end = time(23, 59) if full_day else time(11, 0)
    for day in range(7):
        create_working_hours(
            db,
            tenant_id=tenant.id,
            business_id=biz.id,
            staff_id=None,
            day_of_week=day,
            start_time=time(0, 0) if full_day else time(9, 0),
            end_time=end,
        )
    return tenant.id, biz, svc


def _existing_booking(db, tenant_id, biz, svc, caller_phone, starts_at=None):
    starts_at = starts_at or datetime.now(timezone.utc) + timedelta(hours=3)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone=caller_phone)
    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=starts_at,
    )


def test_press_3_with_no_booking_returns_to_main_menu(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48900000001")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    assert resp.action == IvrAction.CONTINUE
    assert "couldn't find" in resp.prompt.lower()
    db.refresh(session)
    assert session.step == IvrStep.INCOMING
    assert session.invalid_key_count == 0


def test_press_3_with_booking_shows_manage_menu(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000002"
    booking = _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    assert resp.action == IvrAction.CONTINUE
    assert svc.name in resp.prompt
    db.refresh(session)
    assert session.step == IvrStep.MANAGE_BOOKING
    assert session.managed_booking_id == booking.id


def test_manage_booking_cancel_cancels_booking(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000003"
    booking = _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    assert resp.action == IvrAction.END
    db.refresh(session)
    db.refresh(booking)
    assert session.step == IvrStep.BOOKING_CANCELLED
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancel_reason == "customer_ivr_cancel"


def test_manage_booking_back_to_main_menu(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000004"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    assert resp.action == IvrAction.CONTINUE
    assert "appointment" in resp.prompt.lower()
    db.refresh(session)
    assert session.step == IvrStep.INCOMING


def test_manage_booking_invalid_key_increments_counter(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000005"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.step == IvrStep.MANAGE_BOOKING
    assert session.invalid_key_count == 1


def test_manage_booking_reschedule_shows_slots(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000006"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    assert resp.action == IvrAction.CONTINUE
    assert "new time" in resp.prompt.lower()
    db.refresh(session)
    assert session.step == IvrStep.RESCHEDULE_SLOT_SELECTION
    assert session.slot_candidates


def test_reschedule_select_slot_creates_new_booking_and_cancels_old(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000007"
    old_booking = _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    assert resp.action == IvrAction.END
    assert "rescheduled" in resp.prompt.lower()
    db.refresh(session)
    db.refresh(old_booking)
    assert old_booking.status == BookingStatus.CANCELLED
    assert old_booking.cancel_reason == "customer_rescheduled_via_ivr"
    assert session.step == IvrStep.BOOKING_CONFIRMED
    assert session.booking_id is not None
    assert session.booking_id != old_booking.id


def test_reschedule_invalid_slot_key_reprompts(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000008"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.step == IvrStep.RESCHEDULE_SLOT_SELECTION
    assert session.invalid_key_count == 1


def test_repeat_key_at_manage_booking_replays_prompt(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000009"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    initial = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.prompt == initial.prompt
    db.refresh(session)
    assert session.step == IvrStep.MANAGE_BOOKING
    assert session.invalid_key_count == 0


def test_repeat_key_at_reschedule_slot_selection_replays_prompt(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000010"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")
    initial = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.prompt == initial.prompt
    db.refresh(session)
    assert session.step == IvrStep.RESCHEDULE_SLOT_SELECTION
    assert session.invalid_key_count == 0


def test_manage_booking_targets_soonest_upcoming_booking(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000011"
    soonest = _existing_booking(
        db, tenant_id, biz, svc, caller, starts_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    _existing_booking(
        db, tenant_id, biz, svc, caller, starts_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")

    db.refresh(session)
    assert session.managed_booking_id == soonest.id


def test_cancelled_booking_is_terminal(db):
    tenant_id, biz, svc = _setup(db)
    caller = "+48900000012"
    _existing_booking(db, tenant_id, biz, svc, caller)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="3")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    assert resp.action == IvrAction.END
    assert "already complete" in resp.prompt.lower()
