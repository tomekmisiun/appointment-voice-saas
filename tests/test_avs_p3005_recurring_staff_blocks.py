"""P3-005: recurring staff/business blocks (ADR 0003).

`RecurringStaffBlock` subtracts a recurring weekly sub-interval from
generated availability slots, correct by construction against future
`WorkingHours` changes -- unlike the one-off `AvailabilityException`
"replacement window" trick (P3-004), which would go stale if reused for a
recurring case. See `docs/adr/0003-recurring-staff-blocks.md`.
"""
from datetime import date, time

import pytest

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.services.availability_exception_service import create_availability_exception
from app.services.availability_service import get_available_slots
from app.services.business_service import create_business
from app.services.recurring_staff_block_service import (
    create_recurring_staff_block,
    delete_recurring_staff_block,
    require_recurring_staff_block_in_business,
)
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours, update_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _give_admin_membership(db, email: str, business) -> None:
    user = db.query(User).filter(User.email == email).one()
    db.add(BusinessMembership(
        tenant_id=business.tenant_id,
        business_id=business.id,
        user_id=user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()

_DATE = date(2027, 9, 8)  # Wednesday


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Blocks Salon", timezone="UTC")
    service = create_service(
        db, tenant_id=tenant.id, business_id=business.id, name="Cut", duration_minutes=30
    )
    staff_a = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")
    staff_b = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Marek")
    return {
        "tenant_id": tenant.id,
        "business_id": business.id,
        "service_id": service.id,
        "staff_a": staff_a.id,
        "staff_b": staff_b.id,
    }


def _slots_for(db, domain, staff_id):
    return get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=staff_id,
        query_date=_DATE,
    )


# --- CRUD / validation ---


def test_create_business_wide_block(db, domain):
    block = create_recurring_staff_block(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=_DATE.weekday(),
        start_time=time(12, 0),
        end_time=time(13, 0),
        reason="Lunch",
    )
    assert block.staff_id is None


def test_create_staff_specific_block(db, domain):
    block = create_recurring_staff_block(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_a"],
        day_of_week=_DATE.weekday(),
        start_time=time(12, 0),
        end_time=time(13, 0),
        reason="Lunch",
    )
    assert block.staff_id == domain["staff_a"]


def test_create_rejects_staff_from_another_business(db, domain):
    other_business = create_business(
        db, tenant_id=domain["tenant_id"], name="Other Salon", timezone="UTC"
    )
    foreign_staff = create_staff(
        db, tenant_id=domain["tenant_id"], business_id=other_business.id, name="Foreign"
    )

    with pytest.raises(NotFoundError):
        create_recurring_staff_block(
            db,
            tenant_id=domain["tenant_id"],
            business_id=domain["business_id"],
            staff_id=foreign_staff.id,
            day_of_week=_DATE.weekday(),
            start_time=time(12, 0),
            end_time=time(13, 0),
            reason=None,
        )


def test_overlapping_blocks_for_same_scope_rejected(db, domain):
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=2, start_time=time(12, 0), end_time=time(13, 0),
        reason=None,
    )

    with pytest.raises(ConflictError):
        create_recurring_staff_block(
            db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
            staff_id=domain["staff_a"], day_of_week=2,
            start_time=time(12, 30), end_time=time(14, 0), reason=None,
        )


def test_non_overlapping_blocks_for_same_scope_allowed(db, domain):
    first = create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=2, start_time=time(12, 0), end_time=time(13, 0),
        reason="Lunch",
    )
    second = create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=2, start_time=time(15, 0), end_time=time(15, 30),
        reason="Break",
    )
    assert first.id != second.id


def test_overlap_check_scoped_per_staff(db, domain):
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=2, start_time=time(12, 0), end_time=time(13, 0),
        reason=None,
    )
    other = create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_b"], day_of_week=2, start_time=time(12, 0), end_time=time(13, 0),
        reason=None,
    )
    assert other.staff_id == domain["staff_b"]


def test_require_block_in_business_rejects_cross_business_access(db, domain):
    block = create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=None, day_of_week=2, start_time=time(12, 0), end_time=time(13, 0), reason=None,
    )
    other_business = create_business(
        db, tenant_id=domain["tenant_id"], name="Other Salon", timezone="UTC"
    )

    with pytest.raises(NotFoundError):
        require_recurring_staff_block_in_business(
            db, block.id, other_business.id, domain["tenant_id"]
        )


def test_delete_block_rejects_cross_business_access(db, domain):
    block = create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=None, day_of_week=2, start_time=time(12, 0), end_time=time(13, 0), reason=None,
    )
    other_business = create_business(
        db, tenant_id=domain["tenant_id"], name="Other Salon", timezone="UTC"
    )

    with pytest.raises(NotFoundError):
        delete_recurring_staff_block(
            db, block.id, domain["tenant_id"], business_id=other_business.id
        )


# --- availability subtraction correctness ---


def test_recurring_block_splits_working_hours_window(db, domain):
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(17, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch",
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    # 9-12 (3h = 6 slots) + 13-17 (4h = 8 slots) = 14, not 16 (8h unblocked)
    assert len(slots) == 14
    assert not any(s.hour == 12 for s, _ in slots)


def test_recurring_block_stays_correct_after_working_hours_change(db, domain):
    """The ADR's core correctness claim: a recurring block clips whatever
    the *current* schedule is at query time, so it doesn't go stale when
    working hours change after the block was created -- unlike the
    AvailabilityException "replacement window" trick would."""
    staff_wh = create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(17, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch",
    )

    # Working hours change *after* the block already existed.
    update_working_hours(
        db, staff_wh.id, domain["tenant_id"],
        business_id=domain["business_id"], start_time=time(8, 0), end_time=time(20, 0),
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    # New hours: 8:00-20:00 (12h), minus 12:00-13:00 lunch = 11h = 22 slots,
    # and still no slot starting at noon.
    assert len(slots) == 22
    assert not any(s.hour == 12 for s, _ in slots)


def test_business_wide_block_applies_to_all_staff(db, domain):
    for staff_id in (domain["staff_a"], domain["staff_b"]):
        create_working_hours(
            db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
            staff_id=staff_id, day_of_week=_DATE.weekday(),
            start_time=time(9, 0), end_time=time(17, 0),
        )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=None, day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch (everyone)",
    )

    for staff_id in (domain["staff_a"], domain["staff_b"]):
        slots = _slots_for(db, domain, staff_id)
        assert not any(s.hour == 12 for s, _ in slots)


def test_staff_specific_block_does_not_affect_other_staff(db, domain):
    for staff_id in (domain["staff_a"], domain["staff_b"]):
        create_working_hours(
            db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
            staff_id=staff_id, day_of_week=_DATE.weekday(),
            start_time=time(9, 0), end_time=time(17, 0),
        )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch",
    )

    assert not any(s.hour == 12 for s, _ in _slots_for(db, domain, domain["staff_a"]))
    assert any(s.hour == 12 for s, _ in _slots_for(db, domain, domain["staff_b"]))


def test_multiple_blocks_split_into_multiple_gaps(db, domain):
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(18, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch",
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(15, 0), end_time=time(15, 30), reason="Coffee",
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    assert not any(s.hour == 12 for s, _ in slots)
    assert not any(s.hour == 15 and s.minute == 0 for s, _ in slots)
    # 9-12 (6) + 13-15 (4) + 15:30-18 (5) = 15
    assert len(slots) == 15


def test_recurring_block_does_not_apply_on_a_different_weekday(db, domain):
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(17, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=(_DATE.weekday() + 1) % 7,
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch on a different day",
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    assert any(s.hour == 12 for s, _ in slots)
    assert len(slots) == 16


def test_business_wide_closure_still_wins_over_recurring_block(db, domain):
    """AvailabilityException precedence (P3-003) is unchanged: a business
    closure short-circuits to no slots before recurring blocks are even
    considered."""
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(17, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(12, 0), end_time=time(13, 0), reason="Lunch",
    )
    create_availability_exception(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=None, exception_date=_DATE, is_closed=True,
        start_time=None, end_time=None, reason="National holiday",
    )

    assert _slots_for(db, domain, domain["staff_a"]) == []


def test_recurring_block_applies_after_special_hours_exception(db, domain):
    """A recurring block subtracts from a one-off special-hours exception's
    window too, not just plain WorkingHours."""
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(9, 0), end_time=time(17, 0),
    )
    create_recurring_staff_block(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], day_of_week=_DATE.weekday(),
        start_time=time(11, 0), end_time=time(11, 30), reason="Short break",
    )
    create_availability_exception(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_a"], exception_date=_DATE, is_closed=False,
        start_time=time(10, 0), end_time=time(12, 0), reason="Short day",
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    # Exception narrows to 10-12, block then removes 11:00-11:30 from that.
    assert len(slots) == 3  # 10:00, 10:30, 11:30 (11:00 removed)
    assert not any(s.hour == 11 and s.minute == 0 for s, _ in slots)


# --- API layer ---


def test_create_block_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_admin@example.com")
    promote_to_admin(db, "blocks_admin@example.com")
    token = login_user(client, "blocks_admin@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon", timezone="UTC")
    _give_admin_membership(db, "blocks_admin@example.com", business)

    resp = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00", "reason": "Lunch"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 201
    assert resp.json()["staff_id"] is None


def test_create_block_api_requires_admin(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_member@example.com")
    token = login_user(client, "blocks_member@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 2", timezone="UTC")

    resp = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 403


def test_create_block_api_rejects_overlap(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_overlap_admin@example.com")
    promote_to_admin(db, "blocks_overlap_admin@example.com")
    token = login_user(client, "blocks_overlap_admin@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 3", timezone="UTC")
    _give_admin_membership(db, "blocks_overlap_admin@example.com", business)

    first = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_headers(token),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:30:00", "end_time": "14:00:00"},
        headers=auth_headers(token),
    )
    assert second.status_code == 409


def test_get_block_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_get_admin@example.com")
    promote_to_admin(db, "blocks_get_admin@example.com")
    token = login_user(client, "blocks_get_admin@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 4", timezone="UTC")
    _give_admin_membership(db, "blocks_get_admin@example.com", business)
    created = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00", "reason": "Lunch"},
        headers=auth_headers(token),
    ).json()

    resp = client.get(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks/{created['id']}",
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert resp.json()["reason"] == "Lunch"


def test_list_blocks_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_list_admin@example.com")
    promote_to_admin(db, "blocks_list_admin@example.com")
    token = login_user(client, "blocks_list_admin@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 5", timezone="UTC")
    _give_admin_membership(db, "blocks_list_admin@example.com", business)
    client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_headers(token),
    )
    client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 4, "start_time": "15:00:00", "end_time": "15:30:00"},
        headers=auth_headers(token),
    )

    resp = client.get(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    filtered = client.get(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks?day_of_week=4",
        headers=auth_headers(token),
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["day_of_week"] == 4


def test_delete_block_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_delete_admin@example.com")
    promote_to_admin(db, "blocks_delete_admin@example.com")
    token = login_user(client, "blocks_delete_admin@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 6", timezone="UTC")
    _give_admin_membership(db, "blocks_delete_admin@example.com", business)
    created = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_headers(token),
    ).json()

    resp = client.delete(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks/{created['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 204

    get_resp = client.get(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks/{created['id']}",
        headers=auth_headers(token),
    )
    assert get_resp.status_code == 404


def test_delete_block_api_requires_admin(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_delete_admin2@example.com")
    promote_to_admin(db, "blocks_delete_admin2@example.com")
    admin_token = login_user(client, "blocks_delete_admin2@example.com").json()["access_token"]
    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon 7", timezone="UTC")
    _give_admin_membership(db, "blocks_delete_admin2@example.com", business)
    created = client.post(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks",
        json={"day_of_week": 2, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_headers(admin_token),
    ).json()

    register_user(client, "blocks_member2@example.com")
    member_token = login_user(client, "blocks_member2@example.com").json()["access_token"]

    resp = client.delete(
        f"/api/v1/businesses/{business.id}/recurring-staff-blocks/{created['id']}",
        headers=auth_headers(member_token),
    )
    assert resp.status_code == 403
