"""P2-006: let the caller pick a preferred staff member in the IVR.

After choosing a service, if the business has 2+ active staff members the
caller is presented with a staff menu (plus an explicit "any available
staff" option). With 0 or 1 active staff the step is skipped automatically
since there is nothing meaningful to choose between. The chosen staff_id
(or None for "any") is threaded into slot search and the resulting booking.
"""
from datetime import time

from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.business_service import create_business
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.staff_service import create_staff, update_staff
from app.services.working_hours_service import create_working_hours


def _setup_without_staff_hours(db, *, staff_count: int):
    """Like _setup but only business-level working hours are configured
    (no staff-specific schedule) -- mirrors typical seed/demo data where
    staff exist but nobody has set up a per-staff calendar yet."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="No Staff Hours Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    staff = [
        create_staff(db, tenant_id=tenant.id, business_id=biz.id, name=f"Stylist {i + 1}")
        for i in range(staff_count)
    ]
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
    return tenant.id, biz, svc, staff


def _setup(db, *, staff_count: int):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Staff Pick Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    staff = [
        create_staff(db, tenant_id=tenant.id, business_id=biz.id, name=f"Stylist {i + 1}")
        for i in range(staff_count)
    ]
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
        for member in staff:
            create_working_hours(
                db,
                tenant_id=tenant.id,
                business_id=biz.id,
                staff_id=member.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
            )
    return tenant.id, biz, svc, staff


def test_zero_staff_skips_selection_step(db):
    tenant_id, biz, svc, _staff = _setup(db, staff_count=0)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000001")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # main menu -> service

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id is None
    assert response.action.value == "continue"


def test_single_staff_auto_selected_and_skips_menu(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=1)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000002")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id == staff[0].id
    assert response.action.value == "continue"


def test_multiple_staff_presents_selection_menu(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000003")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert any(o.label == "Stylist 1" for o in response.options)
    assert any(o.label == "Stylist 2" for o in response.options)
    assert any(o.key == "0" for o in response.options)


def test_picking_specific_staff_member_moves_to_slot_selection(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000004")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="2")  # Stylist 2

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id == staff[1].id
    assert response.action.value == "continue"


def test_picking_any_available_staff_sets_no_preference(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000005")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="0")  # any available

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id is None
    assert response.action.value == "continue"


def test_invalid_staff_key_re_prompts(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000006")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="9")

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert response.action.value == "continue"


def test_booking_is_created_with_selected_staff_id(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000007")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # Stylist 1

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick slot

    db.refresh(session)
    assert session.step == IvrStep.BOOKING_CONFIRMED
    assert session.booking_id is not None
    assert response.action.value == "end"


def test_no_input_reprompt_at_staff_selection(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000008")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert "didn't hear" in response.prompt.lower()


def test_inactive_staff_excluded_from_selection(db):
    tenant_id, biz, svc, staff = _setup(db, staff_count=2)
    update_staff(db, staff[1].id, biz.id, tenant_id, is_active=False)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000009")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    # only Stylist 1 is active now -> auto-select, skip the menu
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id == staff[0].id


def test_staff_without_own_hours_are_offered_via_business_wide_fallback(db):
    """P3-002: a staff member with no staff-specific WorkingHours row is no
    longer a guaranteed dead-end -- they fall back to the business's hours,
    so they *are* offered in the menu (previously they were excluded, since
    get_available_slots() had no such fallback and would always return no
    slots for them)."""
    tenant_id, biz, svc, staff = _setup_without_staff_hours(db, staff_count=3)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48700000010")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert {o.key for o in response.options} == {"1", "2", "3", "0"}


def test_staff_excluded_only_when_neither_they_nor_business_has_hours(db):
    """The narrower exclusion that remains after P3-002: a staff member is
    only ever a guaranteed dead-end if *neither* they nor the business has
    any working hours configured at all."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="No Hours At All Salon", timezone="UTC")
    create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30)
    for i in range(3):
        create_staff(db, tenant_id=tenant.id, business_id=biz.id, name=f"Stylist {i + 1}")
    # No working hours at all -- neither business-wide nor staff-specific.

    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48700000011")
    handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="1")
    response = handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.NO_SLOTS
    assert response.action.value == "end"
