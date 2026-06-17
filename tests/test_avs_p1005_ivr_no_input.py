"""P1-005: IVR timeout / no-input handling.

key="" represents a no-input event (Twilio sends empty Digits on timeout).
After _NO_INPUT_MAX=3 consecutive no-inputs the session is terminated (EXPIRED).
Between 1 and 2 no-inputs the current step is re-prompted with a
"We didn't hear a response." prefix.
"""
from datetime import time

from app.core.ivr import IvrAction
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.working_hours_service import create_working_hours


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="NoInput Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
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
    return tenant.id, biz, svc


# ---------------------------------------------------------------------------
# No-input at INCOMING step
# ---------------------------------------------------------------------------

def test_no_input_at_main_menu_re_prompts(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000001")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.CONTINUE
    assert "We didn't hear a response" in resp.prompt
    assert resp.session_id == session.id


def test_no_input_increments_counter(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000002")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    db.refresh(session)
    assert session.no_input_count == 1


def test_no_input_second_still_re_prompts(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000003")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.CONTINUE
    assert "We didn't hear" in resp.prompt


def test_no_input_third_terminates_session(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000004")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.END
    assert "session has ended" in resp.prompt

    db.refresh(session)
    assert session.step == IvrStep.EXPIRED


def test_no_input_session_expired_step_set(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000005")

    for _ in range(3):
        handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    db.refresh(session)
    assert session.step == IvrStep.EXPIRED
    assert session.no_input_count == 3


# ---------------------------------------------------------------------------
# No-input at SERVICE_SELECTION step
# ---------------------------------------------------------------------------

def test_no_input_at_service_selection_re_prompts(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000006")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.CONTINUE
    assert "We didn't hear" in resp.prompt
    assert "Haircut" in resp.prompt


# ---------------------------------------------------------------------------
# Valid key still works after no-inputs (counter does not block valid key)
# ---------------------------------------------------------------------------

def test_valid_key_after_no_input_still_works(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000007")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.SERVICE_SELECTION
    assert resp.action == IvrAction.CONTINUE


# ---------------------------------------------------------------------------
# Counter resets on valid key (consecutive semantics)
# ---------------------------------------------------------------------------

def test_no_input_count_resets_on_valid_key(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000009")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    # counter is now 2; a valid key should reset it
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.no_input_count == 0


def test_no_input_after_reset_restarts_count(db):
    """After counter reset, 3 fresh no-inputs are needed to terminate."""
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000010")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # reset
    # Now 2 more no-inputs should still re-prompt (not terminate)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.step != IvrStep.EXPIRED


# ---------------------------------------------------------------------------
# TRANSFER_UNAVAILABLE no-input reprompt
# ---------------------------------------------------------------------------

def test_no_input_at_transfer_unavailable_re_prompts(db):
    tenant_id, biz, _ = _setup(db)
    # transfer_enabled defaults to False, so pressing 2 lands on TRANSFER_UNAVAILABLE
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000011")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")

    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    assert resp.action == IvrAction.CONTINUE
    assert "We didn't hear" in resp.prompt
    assert "main menu" in resp.prompt.lower()


# ---------------------------------------------------------------------------
# Model default
# ---------------------------------------------------------------------------

def test_no_input_count_defaults_to_zero(db):
    tenant_id, biz, _ = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48100000012")
    assert session.no_input_count == 0
