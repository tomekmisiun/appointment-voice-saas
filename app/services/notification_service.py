from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.business import Business
from app.models.customer import Customer
from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
)
from app.models.service import Service


def _format_local_time(starts_at: datetime, business: Business) -> str:
    local = starts_at.astimezone(ZoneInfo(business.timezone))
    return local.strftime("%Y-%m-%d %H:%M")


def enqueue_booking_confirmation(
    db: Session,
    *,
    booking: Booking,
    business: Business,
    customer: Customer,
    service: Service,
) -> list[NotificationOutbox]:
    when = _format_local_time(booking.starts_at, business)

    intents = [
        NotificationOutbox(
            tenant_id=booking.tenant_id,
            business_id=booking.business_id,
            booking_id=booking.id,
            channel=NotificationChannel.SMS,
            purpose=NotificationPurpose.BOOKING_CONFIRMATION,
            recipient_phone=customer.phone,
            body=f"Your {service.name} appointment at {business.name} is confirmed for {when}.",
        )
    ]
    if business.phone:
        intents.append(
            NotificationOutbox(
                tenant_id=booking.tenant_id,
                business_id=booking.business_id,
                booking_id=booking.id,
                channel=NotificationChannel.SMS,
                purpose=NotificationPurpose.BOOKING_CONFIRMATION,
                recipient_phone=business.phone,
                body=f"New booking: {service.name} for {customer.phone} on {when}.",
            )
        )

    for intent in intents:
        db.add(intent)
    db.flush()
    return intents


def enqueue_booking_cancellation(
    db: Session,
    *,
    booking: Booking,
    business: Business,
    customer: Customer,
    service: Service,
) -> list[NotificationOutbox]:
    when = _format_local_time(booking.starts_at, business)

    intents = [
        NotificationOutbox(
            tenant_id=booking.tenant_id,
            business_id=booking.business_id,
            booking_id=booking.id,
            channel=NotificationChannel.SMS,
            purpose=NotificationPurpose.BOOKING_CANCELLATION,
            recipient_phone=customer.phone,
            body=f"Your {service.name} appointment at {business.name} on {when} has been cancelled.",
        )
    ]
    if business.phone:
        intents.append(
            NotificationOutbox(
                tenant_id=booking.tenant_id,
                business_id=booking.business_id,
                booking_id=booking.id,
                channel=NotificationChannel.SMS,
                purpose=NotificationPurpose.BOOKING_CANCELLATION,
                recipient_phone=business.phone,
                body=f"Booking cancelled: {service.name} for {customer.phone} on {when}.",
            )
        )

    for intent in intents:
        db.add(intent)
    db.flush()
    return intents
