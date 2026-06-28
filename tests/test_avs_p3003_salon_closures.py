"""P3-003: salon (business-wide) closures/holidays, and their precedence
over staff-specific exceptions and hours.

`AvailabilityException` already supported a business-wide closure
(`staff_id=None, is_closed=True`) before this task -- exclusion in slot
generation (`test_business_wide_closed_exception_blocks_staff_slots` in
`tests/test_availability.py`) and overlap validation (P3-004) were already
covered. This task adds the missing API clarity (docstring on the create
endpoint) and the precedence/isolation tests the audit flagged as missing:
a business-wide closure must affect *every* staff member and always win
over a staff-specific exception, while a staff-specific exception must
*not* leak into other staff members' or the business-wide search. See
`docs/project/implementation-backlog.md` P3-003 and
`docs/archive/audits/pre-p3-readiness-audit.md` §9-10 item 9.
"""
from datetime import date, time

import pytest

from app.models.tenant import Tenant
from app.services.availability_exception_service import create_availability_exception
from app.services.availability_service import get_available_slots
from app.services.business_service import create_business
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours

_DATE = date(2027, 9, 1)  # Wednesday


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Closures Salon", timezone="UTC")
    service = create_service(
        db, tenant_id=tenant.id, business_id=business.id, name="Cut", duration_minutes=30
    )
    staff_a = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")
    staff_b = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Marek")
    for staff in (staff_a, staff_b):
        create_working_hours(
            db,
            tenant_id=tenant.id,
            business_id=business.id,
            staff_id=staff.id,
            day_of_week=_DATE.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
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


def test_business_wide_closure_blocks_every_staff_member(db, domain):
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        exception_date=_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="National holiday",
    )

    assert _slots_for(db, domain, domain["staff_a"]) == []
    assert _slots_for(db, domain, domain["staff_b"]) == []


def test_staff_specific_closure_does_not_affect_other_staff(db, domain):
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_a"],
        exception_date=_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="Sick day",
    )

    assert _slots_for(db, domain, domain["staff_a"]) == []
    assert _slots_for(db, domain, domain["staff_b"]) != []


def test_staff_specific_closure_does_not_affect_any_available_search(db, domain):
    """A staff-specific exception must never leak into a staff_id=None
    ("any available staff") search -- only a business-wide exception
    (staff_id=None) should."""
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_a"],
        exception_date=_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="Sick day",
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=_DATE.weekday(),
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    assert _slots_for(db, domain, None) != []


def test_business_wide_closure_overrides_staff_specific_special_hours(db, domain):
    """A business-wide closure wins even if the same staff member has a
    staff-specific exception that would otherwise keep them open."""
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_a"],
        exception_date=_DATE,
        is_closed=False,
        start_time=time(9, 0),
        end_time=time(17, 0),
        reason="Working through the holiday",
    )
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        exception_date=_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="National holiday",
    )

    assert _slots_for(db, domain, domain["staff_a"]) == []


def test_business_wide_special_hours_apply_to_staff_specific_search(db, domain):
    """A business-wide special-hours exception (not a closure) narrows a
    staff-specific search too, when that staff has no exception of their
    own for the date."""
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        exception_date=_DATE,
        is_closed=False,
        start_time=time(9, 0),
        end_time=time(11, 0),
        reason="Short day",
    )

    slots = _slots_for(db, domain, domain["staff_a"])

    assert len(slots) == 4  # 2 hours / 30 min, not the full 9:00-17:00 window
