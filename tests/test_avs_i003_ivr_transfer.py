"""Tests for AVS-I003: IVR transfer branch — press 2 resolves transfer destination."""
import pytest

from app.core.ivr import IvrAction
from app.models.business import TransferDestinationPolicy
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business, update_business
from app.services.ivr_service import handle_keypress, start_session
from app.services.staff_service import create_staff


def _make_session(db, biz_id, tenant_id):
    session, _ = start_session(
        db, business_id=biz_id, tenant_id=tenant_id, caller_phone="+48500000001"
    )
    return session


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Transfer IVR Salon", timezone="UTC")
    return {"db": db, "tenant_id": tenant.id, "biz": biz}


# ---------------------------------------------------------------------------
# Transfer disabled
# ---------------------------------------------------------------------------

def test_press_2_transfer_disabled_returns_unavailable_fallback(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    # transfer_enabled defaults to False
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None
    assert any(o.key == "1" for o in resp.options)


def test_press_2_transfer_disabled_sets_transfer_unavailable(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE


# ---------------------------------------------------------------------------
# Transfer enabled — business_phone policy
# ---------------------------------------------------------------------------

def test_press_2_business_phone_policy_transfers_to_business_phone(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        transfer_phone_number="+48100200300",
    )
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.TRANSFER
    assert resp.transfer_destination == "+48100200300"


def test_press_2_business_phone_policy_no_phone_returns_unavailable_fallback(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
    )
    # phone remains None
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None
    assert any(o.key == "1" for o in resp.options)


def test_press_2_business_phone_whitespace_returns_unavailable_fallback(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        transfer_phone_number="   ",
    )
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None


# ---------------------------------------------------------------------------
# Transfer enabled — staff policy
# ---------------------------------------------------------------------------

def test_press_2_staff_policy_transfers_to_first_eligible_staff(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.STAFF,
    )
    create_staff(db, tenant_id=tid, business_id=biz.id, name="Anna", phone="+48777888999")
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.TRANSFER
    assert resp.transfer_destination == "+48777888999"


def test_press_2_staff_policy_no_eligible_staff_returns_unavailable_fallback(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.STAFF,
    )
    # no staff with phone
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None


def test_press_2_staff_policy_inactive_staff_not_used(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.STAFF,
    )
    s = create_staff(db, tenant_id=tid, business_id=biz.id, name="Inactive", phone="+48000000001")
    s.is_active = False
    db.commit()
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE


# ---------------------------------------------------------------------------
# Session state on successful transfer
# ---------------------------------------------------------------------------

def test_successful_transfer_sets_session_step_to_abandoned(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        transfer_phone_number="+48111222333",
    )
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.step == IvrStep.ABANDONED


def test_successful_transfer_persists_destination_on_session(domain):
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        transfer_phone_number="+48444555666",
    )
    session = _make_session(db, biz.id, tid)
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    db.refresh(session)
    assert session.transfer_destination == "+48444555666"
