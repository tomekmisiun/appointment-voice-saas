"""P3-004: one-off staff/business time block hardening.

`AvailabilityException` already supported one-off blocks before this task
(exclusion in slot generation is covered by `tests/test_availability.py`).
This task adds the validation that was missing: overlap/conflict
prevention between exceptions for the same (business_id, staff_id, date)
scope, and a `staff_id` business-membership check on create. See
`docs/project/implementation-backlog.md` P3-004 and
`docs/archive/audits/pre-p3-readiness-audit.md` §9-10 item 6.
"""
from datetime import date, time

import pytest

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.tenant import Tenant
from app.services.availability_exception_service import create_availability_exception
from app.services.availability_service import get_available_slots
from app.services.business_service import create_business
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user

_DATE = date(2027, 8, 4)  # Wednesday


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Blocks Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")
    return {"tenant_id": tenant.id, "business_id": business.id, "staff_id": staff.id}


def _create_exception(db, domain, **overrides):
    kwargs = dict(
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        exception_date=_DATE,
        is_closed=False,
        start_time=time(9, 0),
        end_time=time(12, 0),
        reason="Block",
    )
    kwargs.update(overrides)
    return create_availability_exception(db, **kwargs)


# --- overlap/conflict validation ---


def test_overlapping_special_hours_windows_rejected(db, domain):
    _create_exception(db, domain, start_time=time(9, 0), end_time=time(13, 0))

    with pytest.raises(ConflictError):
        _create_exception(db, domain, start_time=time(12, 0), end_time=time(17, 0))


def test_non_overlapping_special_hours_windows_allowed(db, domain):
    """The existing lunch-block pattern: two non-overlapping windows for
    the same staff/date (9-12 and 13-17) carve out a 12-13 gap."""
    morning = _create_exception(db, domain, start_time=time(9, 0), end_time=time(12, 0))
    afternoon = _create_exception(db, domain, start_time=time(13, 0), end_time=time(17, 0))

    assert morning.id != afternoon.id


def test_adjacent_windows_do_not_overlap(db, domain):
    """A window ending exactly when another starts is not an overlap."""
    first = _create_exception(db, domain, start_time=time(9, 0), end_time=time(12, 0))
    second = _create_exception(db, domain, start_time=time(12, 0), end_time=time(15, 0))

    assert first.id != second.id


def test_closure_conflicts_with_existing_special_hours(db, domain):
    _create_exception(db, domain, is_closed=False, start_time=time(9, 0), end_time=time(12, 0))

    with pytest.raises(ConflictError):
        _create_exception(db, domain, is_closed=True, start_time=None, end_time=None)


def test_special_hours_conflicts_with_existing_closure(db, domain):
    _create_exception(db, domain, is_closed=True, start_time=None, end_time=None)

    with pytest.raises(ConflictError):
        _create_exception(db, domain, is_closed=False, start_time=time(9, 0), end_time=time(12, 0))


def test_second_closure_for_same_scope_rejected(db, domain):
    _create_exception(db, domain, is_closed=True, start_time=None, end_time=None)

    with pytest.raises(ConflictError):
        _create_exception(db, domain, is_closed=True, start_time=None, end_time=None)


def test_overlap_check_scoped_per_staff(db, domain):
    """An overlapping window for a *different* staff member is not a
    conflict -- the check is scoped to the exact staff_id."""
    other_staff = create_staff(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"], name="Marek"
    )

    _create_exception(db, domain, start_time=time(9, 0), end_time=time(12, 0))
    other = _create_exception(
        db, domain, staff_id=other_staff.id, start_time=time(9, 0), end_time=time(12, 0)
    )

    assert other.staff_id == other_staff.id


def test_overlap_check_does_not_cross_business_wide_and_staff_specific(db, domain):
    """Deliberate scope boundary (documented in
    _ensure_no_conflicting_exception's docstring): a business-wide row and
    a staff-specific row for the same date are not cross-checked against
    each other here -- that precedence question belongs to P3-002/003."""
    business_wide = _create_exception(
        db, domain, staff_id=None, start_time=time(9, 0), end_time=time(12, 0)
    )
    staff_specific = _create_exception(
        db, domain, staff_id=domain["staff_id"], start_time=time(9, 0), end_time=time(12, 0)
    )

    assert business_wide.staff_id is None
    assert staff_specific.staff_id == domain["staff_id"]


def test_create_exception_rejects_staff_from_another_business(db, domain):
    other_business = create_business(
        db, tenant_id=domain["tenant_id"], name="Other Salon", timezone="UTC"
    )
    foreign_staff = create_staff(
        db, tenant_id=domain["tenant_id"], business_id=other_business.id, name="Foreign"
    )

    with pytest.raises(NotFoundError):
        _create_exception(db, domain, staff_id=foreign_staff.id)


# --- exclusion / no-cross-staff-effect ---


def test_staff_specific_block_does_not_affect_other_staff_availability(db, domain):
    other_staff = create_staff(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"], name="Marek"
    )
    service = create_service(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        name="Cut", duration_minutes=30,
    )
    for staff_id in (domain["staff_id"], other_staff.id):
        create_working_hours(
            db,
            tenant_id=domain["tenant_id"],
            business_id=domain["business_id"],
            staff_id=staff_id,
            day_of_week=_DATE.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        exception_date=_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="Personal day",
    )

    blocked_staff_slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=service.id,
        staff_id=domain["staff_id"],
        query_date=_DATE,
    )
    other_staff_slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=service.id,
        staff_id=other_staff.id,
        query_date=_DATE,
    )

    assert blocked_staff_slots == []
    assert other_staff_slots != []


# --- API layer ---


def test_create_exception_api_rejects_overlap(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    register_user(client, "blocks_admin@example.com")
    promote_to_admin(db, "blocks_admin@example.com")
    token = login_user(client, "blocks_admin@example.com").json()["access_token"]

    business = create_business(db, tenant_id=tenant.id, name="API Blocks Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")

    first = client.post(
        f"/api/v1/businesses/{business.id}/availability-exceptions",
        json={
            "date": "2027-08-05",
            "is_closed": False,
            "start_time": "09:00:00",
            "end_time": "12:00:00",
            "staff_id": staff.id,
        },
        headers=auth_headers(token),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/businesses/{business.id}/availability-exceptions",
        json={
            "date": "2027-08-05",
            "is_closed": False,
            "start_time": "11:00:00",
            "end_time": "15:00:00",
            "staff_id": staff.id,
        },
        headers=auth_headers(token),
    )
    assert second.status_code == 409
