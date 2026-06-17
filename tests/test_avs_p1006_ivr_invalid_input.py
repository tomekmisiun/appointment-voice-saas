"""P1-006: IVR invalid-input retry counter.

Pressing an unrecognized key at any step increments invalid_key_count.
After _INVALID_KEY_MAX=5 invalid keys the session is terminated (EXPIRED).
The counter is cumulative across steps within a session.
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
    biz = create_business(db, tenant_id=tenant.id, name="InvalidKey Salon", timezone="UTC")
    create_service(
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
    return tenant.id, biz


# ---------------------------------------------------------------------------
# Default value
# ---------------------------------------------------------------------------

def test_invalid_key_count_defaults_to_zero(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000001")
    assert session.invalid_key_count == 0


# ---------------------------------------------------------------------------
# INCOMING step — unknown key
# ---------------------------------------------------------------------------

def test_invalid_key_at_incoming_reprompts(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000002")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.invalid_key_count == 1
    assert session.step == IvrStep.INCOMING


def test_four_invalid_keys_still_reprompt(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000003")

    for _ in range(4):
        resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.invalid_key_count == 4
    assert session.step != IvrStep.EXPIRED


def test_fifth_invalid_key_terminates_session(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000004")

    for _ in range(4):
        handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.END
    assert "Too many invalid inputs" in resp.prompt
    db.refresh(session)
    assert session.step == IvrStep.EXPIRED
    assert session.invalid_key_count == 5


# ---------------------------------------------------------------------------
# SERVICE_SELECTION step — out-of-range key
# ---------------------------------------------------------------------------

def test_invalid_key_at_service_selection_increments_counter(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000005")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")  # invalid

    assert resp.action == IvrAction.CONTINUE
    assert "Invalid choice" in resp.prompt
    db.refresh(session)
    assert session.invalid_key_count == 1


# ---------------------------------------------------------------------------
# TRANSFER_UNAVAILABLE step — any key other than "1"
# ---------------------------------------------------------------------------

def test_invalid_key_at_transfer_unavailable_increments_counter(db):
    """Press 2 at INCOMING → TRANSFER_UNAVAILABLE (transfer disabled), then invalid key."""
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000006")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.invalid_key_count == 1


# ---------------------------------------------------------------------------
# Counter is cumulative across steps
# ---------------------------------------------------------------------------

def test_invalid_key_counter_accumulates_across_steps(db):
    """2 invalid at INCOMING + 3 invalid at SERVICE_SELECTION = terminate on 5th total."""
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000007")

    # 2 invalid keys at INCOMING
    for _ in range(2):
        handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION

    # 2 invalid keys at SERVICE_SELECTION (total 4)
    for _ in range(2):
        handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    db.refresh(session)
    assert session.invalid_key_count == 4
    assert session.step == IvrStep.SERVICE_SELECTION

    # 5th invalid key → terminate
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    assert resp.action == IvrAction.END
    db.refresh(session)
    assert session.step == IvrStep.EXPIRED


# ---------------------------------------------------------------------------
# SLOT_SELECTION step — out-of-range slot key
# ---------------------------------------------------------------------------

def test_invalid_key_at_slot_selection_increments_counter(db):
    """Navigate to SLOT_SELECTION using full-day hours (guarantees slot availability), then press invalid key."""
    tenant_id, biz = _setup(db)
    # Extend working hours to full day so slots are guaranteed regardless of test run time.
    from app.services.working_hours_service import list_working_hours
    whs = list_working_hours(db, tenant_id=tenant_id, business_id=biz.id, staff_id=None)
    for wh in whs:
        wh.start_time = time(0, 0)
        wh.end_time = time(23, 59)
    db.commit()

    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000009")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SERVICE_SELECTION
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # → SLOT_SELECTION

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION

    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")  # invalid slot

    assert resp.action == IvrAction.CONTINUE
    assert "Invalid choice" in resp.prompt
    db.refresh(session)
    assert session.invalid_key_count == 1
    assert session.step == IvrStep.SLOT_SELECTION


# ---------------------------------------------------------------------------
# Valid key does not increment counter
# ---------------------------------------------------------------------------

def test_valid_key_does_not_increment_invalid_counter(db):
    tenant_id, biz = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48200000008")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")  # invalid
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # valid

    db.refresh(session)
    assert session.invalid_key_count == 1  # only the first press counted
    assert session.step == IvrStep.SERVICE_SELECTION
