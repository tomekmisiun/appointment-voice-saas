"""P1-007: IVR repeat-menu option.

Pressing "*" at any interactive step replays the current prompt without
advancing the session, incrementing invalid_key_count, or incrementing
no_input_count. Digits are never repeat keys: menus can present up to 9
services/slots, so "9" must remain a live selection (see P1-006 tests,
which rely on "9" being treated as an out-of-range/invalid digit).
"""
from datetime import time

from app.core.ivr import IvrAction
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.working_hours_service import create_working_hours


def _setup(db, *, full_day: bool = False):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Repeat Salon", timezone="UTC")
    create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
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
    return tenant.id, biz


# ---------------------------------------------------------------------------
# INCOMING step
# ---------------------------------------------------------------------------

def test_repeat_key_star_at_incoming_replays_prompt(db):
    tenant_id, biz = _setup(db)
    session, initial = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000002")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.prompt == initial.prompt
    db.refresh(session)
    assert session.step == IvrStep.INCOMING


def test_repeat_does_not_increment_invalid_key_count(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000003")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    db.refresh(session)
    assert session.invalid_key_count == 0


def test_repeat_resets_no_input_count(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000004")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")  # no-input → count=1
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")  # repeat → reset

    db.refresh(session)
    assert session.no_input_count == 0


def test_digit_9_at_incoming_is_not_a_repeat_key(db):
    """Digits are live menu keys, not repeat keys, so "9" at INCOMING is invalid input."""
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000008")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.invalid_key_count == 1


# ---------------------------------------------------------------------------
# SERVICE_SELECTION step
# ---------------------------------------------------------------------------

def test_repeat_at_service_selection_replays_service_menu(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000005")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.action == IvrAction.CONTINUE
    assert "Haircut" in resp.prompt
    db.refresh(session)
    assert session.step == IvrStep.SERVICE_SELECTION
    assert session.invalid_key_count == 0


# ---------------------------------------------------------------------------
# SLOT_SELECTION step
# ---------------------------------------------------------------------------

def test_repeat_at_slot_selection_replays_slot_menu(db):
    tenant_id, biz = _setup(db, full_day=True)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000006")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SLOT_SELECTION

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.action == IvrAction.CONTINUE
    assert "slot" in resp.prompt.lower()
    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.invalid_key_count == 0


# ---------------------------------------------------------------------------
# TRANSFER_UNAVAILABLE step
# ---------------------------------------------------------------------------

def test_digit_9_selects_ninth_service_when_present(db):
    """Regression guard: the 9th service must stay selectable via "9", not be eaten by repeat."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Nine Service Salon", timezone="UTC")
    for i in range(9):
        create_service(
            db, tenant_id=tenant.id, business_id=biz.id, name=f"Service {i + 1}", duration_minutes=30
        )
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
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48300000009")
    handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="1")  # → SERVICE_SELECTION

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="9")

    db.refresh(session)
    assert session.selected_service_id is not None
    assert session.invalid_key_count == 0
    assert resp.action == IvrAction.CONTINUE


def test_repeat_at_transfer_unavailable_replays_prompt(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48300000007")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")  # → TRANSFER_UNAVAILABLE
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="*")

    assert resp.action == IvrAction.CONTINUE
    assert "main menu" in resp.prompt.lower()
    assert session.invalid_key_count == 0
