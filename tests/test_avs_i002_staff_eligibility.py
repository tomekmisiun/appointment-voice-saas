"""Tests for AVS-I002: staff transfer eligibility."""
import pytest

from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.staff_service import create_staff, get_eligible_transfer_staff, update_staff


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Eligibility Test Salon", timezone="UTC")
    return {"db": db, "tenant_id": tenant.id, "business_id": biz.id}


# ---------------------------------------------------------------------------
# Basic eligibility
# ---------------------------------------------------------------------------

def test_active_staff_with_phone_is_eligible(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    create_staff(db, tenant_id=tid, business_id=bid, name="Alice", phone="+48123456789")
    result = get_eligible_transfer_staff(db, bid, tid)
    assert len(result) == 1
    assert result[0].name == "Alice"


def test_staff_without_phone_is_excluded(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    create_staff(db, tenant_id=tid, business_id=bid, name="Bob", phone=None)
    result = get_eligible_transfer_staff(db, bid, tid)
    assert result == []


def test_staff_with_empty_phone_is_excluded(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    s = create_staff(db, tenant_id=tid, business_id=bid, name="Carol")
    s.phone = ""
    db.commit()
    result = get_eligible_transfer_staff(db, bid, tid)
    assert result == []


def test_staff_with_whitespace_phone_is_excluded(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    s = create_staff(db, tenant_id=tid, business_id=bid, name="Carol2")
    s.phone = "   "
    db.commit()
    result = get_eligible_transfer_staff(db, bid, tid)
    assert result == []


def test_inactive_staff_with_phone_is_excluded(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    s = create_staff(db, tenant_id=tid, business_id=bid, name="Dave", phone="+48999000111")
    update_staff(db, s.id, tid, is_active=False)
    result = get_eligible_transfer_staff(db, bid, tid)
    assert result == []


def test_multiple_eligible_staff_returned_in_id_order(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    a = create_staff(db, tenant_id=tid, business_id=bid, name="Eve", phone="+48100000001")
    b = create_staff(db, tenant_id=tid, business_id=bid, name="Frank", phone="+48100000002")
    result = get_eligible_transfer_staff(db, bid, tid)
    assert [s.id for s in result] == [a.id, b.id]


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

def test_eligible_staff_is_tenant_scoped(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    create_staff(db, tenant_id=tid, business_id=bid, name="Grace", phone="+48200000001")
    result_correct = get_eligible_transfer_staff(db, bid, tid)
    result_wrong = get_eligible_transfer_staff(db, bid, tid + 9999)
    assert len(result_correct) == 1
    assert result_wrong == []


def test_eligible_staff_is_business_scoped(domain, db):
    tid = domain["tenant_id"]
    biz_a_id = domain["business_id"]
    biz_b = create_business(db, tenant_id=tid, name="Other Salon", timezone="UTC")

    create_staff(db, tenant_id=tid, business_id=biz_a_id, name="Heidi", phone="+48300000001")

    result_a = get_eligible_transfer_staff(db, biz_a_id, tid)
    result_b = get_eligible_transfer_staff(db, biz_b.id, tid)
    assert len(result_a) == 1
    assert result_b == []


# ---------------------------------------------------------------------------
# Mixed staff — only eligible ones returned
# ---------------------------------------------------------------------------

def test_only_eligible_staff_returned_in_mixed_pool(domain):
    db, tid, bid = domain["db"], domain["tenant_id"], domain["business_id"]
    eligible = create_staff(db, tenant_id=tid, business_id=bid, name="Ivan", phone="+48400000001")
    create_staff(db, tenant_id=tid, business_id=bid, name="Judy", phone=None)
    inactive = create_staff(db, tenant_id=tid, business_id=bid, name="Karl", phone="+48400000002")
    update_staff(db, inactive.id, tid, is_active=False)

    result = get_eligible_transfer_staff(db, bid, tid)
    assert len(result) == 1
    assert result[0].id == eligible.id
