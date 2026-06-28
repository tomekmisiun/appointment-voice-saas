"""Tests for IVR simulation service (AVS-G001–G009)."""

from datetime import time, timedelta, timezone, datetime as dt

import pytest

from app.core.domain_errors import NotFoundError
from app.core.ivr import IvrAction
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business, update_business
from app.services.customer_service import get_or_create_customer
from app.services.ivr_service import (
    expire_stale_sessions,
    handle_keypress,
    start_session,
)
from app.services.service_service import create_service
from app.services.working_hours_service import create_working_hours


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="IVR Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    # Create business-level working hours for all days (staff_id=None)
    for day in range(7):
        create_working_hours(
            db,
            tenant_id=tenant.id,
            business_id=biz.id,
            staff_id=None,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
    return tenant.id, biz, svc


# --- G001: VoiceSession model ---

def test_start_session_creates_voice_session(db):
    tenant_id, biz, _svc = _setup(db)

    session, response = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111222"
    )

    assert session.id is not None
    assert session.step == IvrStep.INCOMING
    assert session.tenant_id == tenant_id
    assert session.business_id == biz.id
    assert session.caller_phone == "+48600111222"
    assert session.expires_at > dt.now(tz=timezone.utc)


def test_start_session_returns_main_menu(db):
    tenant_id, biz, _svc = _setup(db)

    _session, response = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111222"
    )

    assert response.session_id is not None
    assert "1" in response.prompt or any(o.key == "1" for o in response.options)
    assert response.action == IvrAction.CONTINUE


def test_start_session_rejects_unknown_business(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()

    with pytest.raises(NotFoundError):
        start_session(db, business_id=99999, tenant_id=tenant.id, caller_phone="+48600111222")


# --- P3-009 follow-up: per-business IVR locale ---


def test_start_session_defaults_to_english_locale(db):
    tenant_id, biz, _svc = _setup(db)

    session, response = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111223"
    )

    assert session.locale == "en"
    assert "Welcome" in response.prompt


def test_start_session_uses_business_polish_language(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(
        db, tenant_id=tenant.id, name="Salon Polski", timezone="UTC", language="pl"
    )

    session, response = start_session(
        db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48600111224"
    )

    assert session.locale == "pl"
    assert "Witamy" in response.prompt


def test_changing_business_language_does_not_affect_in_progress_session(db):
    """A call already in progress keeps its original locale even if the
    business's language setting changes mid-call -- VoiceSession.locale is
    a snapshot taken at session creation, not a live lookup."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(
        db, tenant_id=tenant.id, name="Salon Zmiana", timezone="UTC", language="pl"
    )
    session, _response = start_session(
        db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48600111225"
    )
    assert session.locale == "pl"

    update_business(db, biz.id, tenant.id, language="en")

    db.refresh(session)
    assert session.locale == "pl"


# --- G004: Main menu ---

def test_press_1_transitions_to_service_selection(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111333")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.SERVICE_SELECTION
    assert response.action == IvrAction.CONTINUE
    assert len(response.options) >= 1


def test_press_2_transfers(db):
    tenant_id, biz, _svc = _setup(db)
    update_business(db, biz.id, tenant_id, transfer_enabled=True, transfer_phone_number="+48100200300")
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111444")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    db.refresh(session)
    assert session.step == IvrStep.ABANDONED
    assert response.action == IvrAction.TRANSFER
    assert response.transfer_destination == "+48100200300" 


def test_invalid_key_at_main_menu_re_prompts(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600111555")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    db.refresh(session)
    assert session.step == IvrStep.INCOMING
    assert response.action == IvrAction.CONTINUE


# --- G005: Service selection ---

def test_press_1_in_service_selection_moves_to_slot_selection(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600122111")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # main menu → service

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_service_id == _svc.id
    assert session.slot_candidates is not None
    assert response.action == IvrAction.CONTINUE
    assert len(response.options) >= 1


def test_invalid_service_key_re_prompts(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600122222")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    db.refresh(session)
    assert session.step == IvrStep.SERVICE_SELECTION
    assert response.action == IvrAction.CONTINUE


# --- G006/G007: Slot selection and booking ---

def test_press_1_in_slot_selection_creates_booking(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600133111")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.BOOKING_CONFIRMED
    assert session.booking_id is not None
    assert response.action == IvrAction.END
    assert "booked" in response.prompt.lower() or "appointment" in response.prompt.lower()


def test_booking_creates_customer_from_caller_phone(db):
    tenant_id, biz, _svc = _setup(db)
    caller = "+48600133222"
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone=caller)
    assert customer.id is not None
    db.refresh(session)
    assert session.booking_id is not None


def test_invalid_slot_key_re_prompts(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600133333")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert response.action == IvrAction.CONTINUE


# --- G008: No available slots ---

def test_no_slots_ends_session(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Empty Salon", timezone="UTC")
    create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30
    )
    # No working hours → no slots available

    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48600144111")
    handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.NO_SLOTS
    assert response.action == IvrAction.END


# --- Session isolation ---

def test_handle_keypress_rejects_wrong_tenant(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600155111")

    with pytest.raises(NotFoundError):
        handle_keypress(db, session_id=session.id, tenant_id=99999, key="1")


def test_terminal_session_cannot_be_continued(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600155222")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → BOOKING_CONFIRMED

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    assert response.action == IvrAction.END


# --- G009: Session expiration ---

def test_expired_session_returns_end_response(db, monkeypatch):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600166111")

    # Back-date expiry
    session.expires_at = dt.now(tz=timezone.utc) - timedelta(seconds=1)
    db.commit()

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.EXPIRED
    assert response.action == IvrAction.END


def test_expire_stale_sessions_marks_old_sessions(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600166222")
    session.expires_at = dt.now(tz=timezone.utc) - timedelta(minutes=15)
    db.commit()

    count = expire_stale_sessions(db)

    db.refresh(session)
    assert count >= 1
    assert session.step == IvrStep.EXPIRED


def test_expire_stale_sessions_skips_terminal_sessions(db):
    tenant_id, biz, _svc = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48600166333")
    session.expires_at = dt.now(tz=timezone.utc) - timedelta(minutes=15)
    session.step = IvrStep.BOOKING_CONFIRMED
    db.commit()

    expire_stale_sessions(db)

    db.refresh(session)
    assert session.step == IvrStep.BOOKING_CONFIRMED
