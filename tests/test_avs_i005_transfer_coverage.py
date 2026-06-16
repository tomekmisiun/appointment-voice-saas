"""AVS-I005: validate transfer behavior end-to-end — covers remaining gaps."""
import pytest

from app.core.ivr import IvrAction
from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business, update_business
from app.services.ivr_service import handle_keypress, start_session


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="I005 Salon", timezone="UTC")
    return {"db": db, "tenant_id": tenant.id, "biz": biz}


def _make_session(db, biz_id, tenant_id):
    session, _ = start_session(
        db, business_id=biz_id, tenant_id=tenant_id, caller_phone="+48500000005"
    )
    return session


def test_unknown_transfer_policy_returns_unavailable_fallback(domain):
    """An unrecognised policy value must not transfer — returns TRANSFER_UNAVAILABLE."""
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(db, biz.id, tid, transfer_enabled=True)
    # Force an unknown policy value directly on the model
    biz.transfer_destination_policy = "unknown_future_policy"
    db.commit()

    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")

    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None


def test_transfer_flow_business_phone_full_path(domain):
    """Full press-2 → TRANSFER path with business_phone policy."""
    from app.models.business import TransferDestinationPolicy
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        phone="+48600700800",
    )
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")

    db.refresh(session)
    assert resp.action == IvrAction.TRANSFER
    assert resp.transfer_destination == "+48600700800"
    assert session.step == IvrStep.ABANDONED
    assert session.transfer_destination == "+48600700800"


def test_transfer_unavailable_then_press_1_then_transfer_succeeds(domain):
    """Caller hits unavailable, returns to menu, presses 2 again after transfer is fixed."""
    from app.models.business import TransferDestinationPolicy
    db, tid, biz = domain["db"], domain["tenant_id"], domain["biz"]
    # First: transfer disabled
    session = _make_session(db, biz.id, tid)
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.CONTINUE
    db.refresh(session)
    assert session.step == IvrStep.TRANSFER_UNAVAILABLE

    # Press 1 to go back to menu
    handle_keypress(db, session_id=session.id, tenant_id=tid, key="1")
    db.refresh(session)
    assert session.step == IvrStep.INCOMING

    # Now enable transfer and press 2 again
    update_business(
        db, biz.id, tid,
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        phone="+48999888777",
    )
    resp = handle_keypress(db, session_id=session.id, tenant_id=tid, key="2")
    assert resp.action == IvrAction.TRANSFER
    assert resp.transfer_destination == "+48999888777"
