from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.job_queue import Job, enqueue_job
from app.core.sms import SmsMessage
from app.models.booking import Booking
from app.models.business import Business
from app.models.customer import Customer
from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.service import Service
from app.services.sms_provider import SmsProvider, get_sms_provider

SEND_NOTIFICATION_JOB = "send_notification"
MAX_NOTIFICATION_ATTEMPTS = 3


class SmsDeliveryError(Exception):
    pass


def enqueue_send_notification_job(notification_id: int) -> Job:
    return enqueue_job(SEND_NOTIFICATION_JOB, {"notification_id": notification_id})


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


def send_notification_in_worker(
    db: Session,
    *,
    notification_id: int,
    sms_provider: SmsProvider | None = None,
) -> None:
    intent = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.id == notification_id)
        .first()
    )

    if intent is None or intent.status != NotificationStatus.PENDING:
        return

    sms_provider = sms_provider or get_sms_provider()
    result = sms_provider.send(SmsMessage(to=intent.recipient_phone, body=intent.body))

    intent.attempts += 1

    if result.success:
        intent.status = NotificationStatus.SENT
        intent.sent_at = datetime.now(timezone.utc)
        db.commit()
        return

    intent.last_error = result.error
    if intent.attempts >= MAX_NOTIFICATION_ATTEMPTS:
        intent.status = NotificationStatus.FAILED
        db.commit()
        return
    db.commit()
    raise SmsDeliveryError(result.error)
