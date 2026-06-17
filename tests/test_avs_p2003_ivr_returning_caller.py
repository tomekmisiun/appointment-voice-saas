"""P2-003: recognize returning caller in the IVR.

start_session() personalizes the main-menu greeting when caller_phone
matches an existing Customer for this exact business+tenant, preferring
the richer Client profile name if one is linked. Never looks across
business/tenant boundaries — only ever uses the exact match already
enforced by get_customer_by_phone()/get_client_by_customer_id().
"""
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.client_service import create_client
from app.services.customer_service import get_or_create_customer
from app.services.ivr_service import start_session


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Returning Caller Salon", timezone="UTC")
    return tenant.id, biz


def test_unknown_caller_gets_generic_greeting(db):
    tenant_id, biz = _setup(db)

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48720000001"
    )

    assert "welcome back" not in resp.prompt.lower()
    assert resp.prompt.startswith("Welcome!")


def test_known_customer_without_client_gets_personalized_greeting(db):
    tenant_id, biz = _setup(db)
    get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48720000002", name="Kasia"
    )

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48720000002"
    )

    assert "Welcome back, Kasia!" in resp.prompt


def test_known_customer_without_name_gets_generic_greeting(db):
    tenant_id, biz = _setup(db)
    get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48720000003")

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48720000003"
    )

    assert "welcome back" not in resp.prompt.lower()


def test_linked_client_name_takes_priority_over_customer_name(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48720000004", name="K."
    )
    create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Katarzyna Nowak", customer_id=customer.id
    )

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48720000004"
    )

    assert "Welcome back, Katarzyna Nowak!" in resp.prompt


def test_caller_from_different_business_is_not_recognized(db):
    tenant_id, biz = _setup(db)
    other_biz = create_business(db, tenant_id=tenant_id, name="Other Salon", timezone="UTC")
    get_or_create_customer(
        db, tenant_id=tenant_id, business_id=other_biz.id, phone="+48720000005", name="Cross Biz"
    )

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48720000005"
    )

    assert "welcome back" not in resp.prompt.lower()


def test_unknown_phone_value_does_not_crash(db):
    tenant_id, biz = _setup(db)

    _session, resp = start_session(
        db, business_id=biz.id, tenant_id=tenant_id, caller_phone="unknown"
    )

    assert "welcome back" not in resp.prompt.lower()
