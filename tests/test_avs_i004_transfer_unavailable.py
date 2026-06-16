"""Tests for AVS-I004: transfer unavailable fallback — TRANSFER_UNAVAILABLE step."""
import pytest

from app.core.ivr import IvrAction
from app.models.business import TransferDestinationPolicy
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business, update_business
from app.services.ivr_service import handle_keypress, start_session


def _make_session(db, biz_id, tenant_id):
    session, _ = start_session(
        db, business_id=biz_id, tenant_id=tenant_id, caller_phone="+48500000099"
    )
    return session


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Fallback IVR Salon", timezone="UTC")
    return {"db": db, "tenant_id": tenant.id, "biz": biz}


# ---------------------------------------------------------------------------
# Transfer disabled → TRANSFER_UNAVAILABLE step
# ---------------------------------------------------------------------------

def test_transfer_disabled_sets_transfer_unavailable_step(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    # transfer_enabled defaults to False
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE


def test_transfer_disabled_response_is_continue_not_end(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    assert any(o.key == "1" for o in resp.options)


# ---------------------------------------------------------------------------
# No destination → TRANSFER_UNAVAILABLE step
# ---------------------------------------------------------------------------

def test_no_destination_staff_policy_sets_transfer_unavailable(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.STAFF,
    )
    # no staff at all
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE


def test_no_destination_business_phone_policy_sets_transfer_unavailable(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        # phone remains None
    )
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE


# ---------------------------------------------------------------------------
# Press 1 in TRANSFER_UNAVAILABLE → return to main menu
# ---------------------------------------------------------------------------

def test_press_1_from_transfer_unavailable_returns_to_incoming(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")  # → TRANSFER_UNAVAILABLE
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="1")
    db.refresh(session)
    assert session.step == IvrStep.INCOMING
    assert resp.action == IvrAction.CONTINUE
    assert "1" in resp.prompt or any(o.key == "1" for o in resp.options)


def test_press_1_from_transfer_unavailable_shows_main_menu(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="1")
    assert "book" in resp.prompt.lower() or "appointment" in resp.prompt.lower()


def test_invalid_key_from_transfer_unavailable_re_prompts(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="9")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE
    assert resp.action == IvrAction.CONTINUE


# ---------------------------------------------------------------------------
# Transfer unavailable is NOT a terminal state (can be expired by TTL)
# ---------------------------------------------------------------------------

def test_transfer_unavailable_session_can_still_be_expired(domain):
    """TRANSFER_UNAVAILABLE is not in the do-not-expire list; TTL applies."""
    from datetime import datetime, timezone, timedelta
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")

    # Force the session to look expired
    session.expires_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
    db.commit()

    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="1")
    assert resp.action == IvrAction.END
