"""P2-007: suggest the caller's last-used staff member in the IVR.

When the staff-selection menu (P2-006) is presented, the caller's most
recent past booking with this business is checked for a staff_id. If that
staff member is still active and schedulable, they are reordered to the
front of the menu (so they're always option "1") and called out by name in
the prompt. With no booking history, or a last staff member who is no
longer active/schedulable, the menu is unaffected (same as plain P2-006).
"""
from datetime import time

from app.models.tenant import Tenant
from app.models.voice_session import IvrStep
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.staff_service import create_staff, update_staff
from app.services.working_hours_service import create_working_hours


def _setup(db, *, staff_count: int = 2):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Last Staff Salon", timezone="UTC")
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


def _give_past_booking_with_staff(db, *, tenant_id, biz, svc, staff_member, caller_phone):
    from datetime import datetime, timedelta, timezone

    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone=caller_phone, name="Returning"
    )
    create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_member.id,
        starts_at=datetime.now(timezone.utc) - timedelta(days=7),
    )
    return customer


def test_no_history_leaves_menu_unaffected(db):
    tenant_id, biz, svc, staff = _setup(db)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone="+48710000001")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert "who you saw last time" not in response.prompt.lower()
    assert any(o.label == "Stylist 1" for o in response.options)


def test_last_staff_member_is_offered_first_and_called_out(db):
    tenant_id, biz, svc, staff = _setup(db)
    caller = "+48710000002"
    _give_past_booking_with_staff(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff_member=staff[1], caller_phone=caller
    )
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert f"press 1 for {staff[1].name}, who you saw last time" in response.prompt
    assert response.options[0].label == staff[1].name


def test_pressing_1_books_with_last_staff_member(db):
    tenant_id, biz, svc, staff = _setup(db)
    caller = "+48710000003"
    _give_past_booking_with_staff(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff_member=staff[1], caller_phone=caller
    )
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # press 1 -> last staff

    db.refresh(session)
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id == staff[1].id


def test_inactive_last_staff_member_is_not_suggested(db):
    tenant_id, biz, svc, staff = _setup(db)
    caller = "+48710000004"
    _give_past_booking_with_staff(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff_member=staff[1], caller_phone=caller
    )
    update_staff(db, staff[1].id, tenant_id, is_active=False)
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    # only Stylist 1 remains active/schedulable -> auto-select, skip menu entirely
    assert session.step == IvrStep.SLOT_SELECTION
    assert session.selected_staff_id == staff[0].id
    assert "who you saw last time" not in response.prompt.lower()


def test_reprompt_after_no_input_keeps_last_staff_first(db):
    tenant_id, biz, svc, staff = _setup(db)
    caller = "+48710000005"
    _give_past_booking_with_staff(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff_member=staff[1], caller_phone=caller
    )
    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="")

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert response.options[0].label == staff[1].name


def test_caller_from_different_business_history_is_not_suggested(db):
    tenant_id, biz, svc, staff = _setup(db)
    other_biz = create_business(db, tenant_id=tenant_id, name="Other Salon", timezone="UTC")
    other_svc = create_service(
        db, tenant_id=tenant_id, business_id=other_biz.id, name="Cut", duration_minutes=30
    )
    other_staff = create_staff(db, tenant_id=tenant_id, business_id=other_biz.id, name="Other Stylist")
    caller = "+48710000006"
    _give_past_booking_with_staff(
        db, tenant_id=tenant_id, biz=other_biz, svc=other_svc, staff_member=other_staff, caller_phone=caller
    )

    session, _ = start_session(db, business_id=biz.id, tenant_id=tenant_id, caller_phone=caller)
    handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")

    response = handle_keypress(db, session_id=session.id, tenant_id=tenant_id, key="1")  # pick service

    db.refresh(session)
    assert session.step == IvrStep.STAFF_SELECTION
    assert "who you saw last time" not in response.prompt.lower()
