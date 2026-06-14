"""Tests for the notification outbox model (AVS-E001)."""

from datetime import datetime, timezone

from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Outbox Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48600100200"
    )
    return tenant.id, biz.id, staff.id, svc.id, customer.id


def test_notification_outbox_persists_with_defaults(db):
    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=datetime(2027, 9, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    intent = NotificationOutbox(
        tenant_id=tenant_id,
        business_id=biz_id,
        booking_id=booking.id,
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.BOOKING_CONFIRMATION,
        recipient_phone="+48600100200",
        body="Your booking is confirmed.",
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    assert intent.id is not None
    assert intent.status == NotificationStatus.PENDING
    assert intent.attempts == 0
    assert intent.sent_at is None
    assert intent.booking_id == booking.id


def test_notification_outbox_can_be_created_without_booking(db):
    tenant_id, biz_id, _staff_id, _svc_id, _customer_id = _setup(db)

    intent = NotificationOutbox(
        tenant_id=tenant_id,
        business_id=biz_id,
        booking_id=None,
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.BOOKING_CANCELLATION,
        recipient_phone="+48600100200",
        body="Your booking was cancelled.",
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    assert intent.id is not None
    assert intent.booking_id is None


def test_notification_outbox_query_scoped_to_tenant(db):
    tenant_id, biz_id, _staff_id, _svc_id, _customer_id = _setup(db)

    other_tenant = Tenant(slug="outbox-other", name="Other Biz", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)

    db.add_all(
        [
            NotificationOutbox(
                tenant_id=tenant_id,
                business_id=biz_id,
                purpose=NotificationPurpose.BOOKING_CONFIRMATION,
                recipient_phone="+48600100200",
                body="Tenant A message",
            ),
            NotificationOutbox(
                tenant_id=other_tenant.id,
                business_id=biz_id,
                purpose=NotificationPurpose.BOOKING_CONFIRMATION,
                recipient_phone="+48600100200",
                body="Tenant B message",
            ),
        ]
    )
    db.commit()

    results = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.tenant_id == tenant_id)
        .all()
    )

    bodies = {r.body for r in results}
    assert "Tenant A message" in bodies
    assert "Tenant B message" not in bodies
