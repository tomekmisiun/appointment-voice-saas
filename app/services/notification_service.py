from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.job_queue import Job, enqueue_job
from app.core.metrics import observe_sms_provider_request
from app.core.sms import SmsMessage
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.models.customer import Customer
from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.service import Service
from app.models.waitlist_entry import WaitlistEntry
from app.services.booking_public_service import build_public_management_url
from app.services.business_service import require_business
from app.services.customer_service import require_customer_in_business
from app.services.service_service import require_service_in_business
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

    manage_url = build_public_management_url(booking.id)
    manage_suffix = f" Manage: {manage_url}" if manage_url else ""

    intents = [
        NotificationOutbox(
            tenant_id=booking.tenant_id,
            business_id=booking.business_id,
            booking_id=booking.id,
            channel=NotificationChannel.SMS,
            purpose=NotificationPurpose.BOOKING_CONFIRMATION,
            recipient_phone=customer.phone,
            body=f"Your {service.name} appointment at {business.name} is confirmed for {when}.{manage_suffix}",
        )
    ]
    if business.owner_notification_phone:
        intents.append(
            NotificationOutbox(
                tenant_id=booking.tenant_id,
                business_id=booking.business_id,
                booking_id=booking.id,
                channel=NotificationChannel.SMS,
                purpose=NotificationPurpose.BOOKING_CONFIRMATION,
                recipient_phone=business.owner_notification_phone,
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
    if business.owner_notification_phone:
        intents.append(
            NotificationOutbox(
                tenant_id=booking.tenant_id,
                business_id=booking.business_id,
                booking_id=booking.id,
                channel=NotificationChannel.SMS,
                purpose=NotificationPurpose.BOOKING_CANCELLATION,
                recipient_phone=business.owner_notification_phone,
                body=f"Booking cancelled: {service.name} for {customer.phone} on {when}.",
            )
        )

    for intent in intents:
        db.add(intent)
    db.flush()
    return intents


def enqueue_waitlist_offer(
    db: Session,
    *,
    entry: WaitlistEntry,
    business: Business,
    customer: Customer,
    service: Service,
) -> NotificationOutbox:
    when = entry.desired_date.strftime("%Y-%m-%d")
    intent = NotificationOutbox(
        tenant_id=entry.tenant_id,
        business_id=entry.business_id,
        booking_id=None,
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.WAITLIST_OFFER,
        recipient_phone=customer.phone,
        body=(
            f"Good news! A {service.name} slot opened up at {business.name} "
            f"on {when}. Call us to book it."
        ),
    )
    db.add(intent)
    db.flush()
    return intent


def enqueue_external_booking_link_sms(
    db: Session,
    *,
    business: Business,
    caller_phone: str,
    url: str,
    label: str | None = None,
) -> NotificationOutbox:
    label_text = label or "Book online"
    intent = NotificationOutbox(
        tenant_id=business.tenant_id,
        business_id=business.id,
        booking_id=None,
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.EXTERNAL_BOOKING_LINK,
        recipient_phone=caller_phone,
        body=f"{label_text}: {url}",
    )
    db.add(intent)
    db.flush()
    return intent


def enqueue_due_reminders(db: Session) -> int:
    """Enqueue a reminder SMS for confirmed bookings starting within the
    reminder lead window. Idempotent: skips bookings that already have a
    BOOKING_REMINDER outbox row, so it is safe to call on every maintenance
    tick regardless of cadence.

    Skips bookings made with less than `settings.reminder_min_advance_minutes`
    of notice (e.g. booked today for tomorrow) -- those bookings are already
    within the reminder lead window the moment they're created, so a
    reminder would land minutes after the confirmation SMS for no reason.
    The two settings are independent and both deliberately default to the
    same value (1440 = 1 day): reminder_lead_minutes controls how close to
    the appointment the reminder fires; reminder_min_advance_minutes
    controls whether the *original booking* was made far enough ahead for a
    reminder to be worth sending at all."""
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(minutes=settings.reminder_lead_minutes)
    min_advance = timedelta(minutes=settings.reminder_min_advance_minutes)

    due_bookings = (
        db.query(Booking)
        .filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at > now,
            Booking.starts_at <= threshold,
        )
        .all()
    )

    count = 0
    for booking in due_bookings:
        if booking.starts_at - booking.created_at < min_advance:
            continue

        already_queued = (
            db.query(NotificationOutbox)
            .filter(
                NotificationOutbox.booking_id == booking.id,
                NotificationOutbox.purpose == NotificationPurpose.BOOKING_REMINDER,
            )
            .first()
        )
        if already_queued is not None:
            continue

        business = require_business(db, booking.business_id, booking.tenant_id)
        customer = require_customer_in_business(
            db, booking.customer_id, booking.business_id, booking.tenant_id
        )
        service = require_service_in_business(db, booking.service_id, booking.business_id, booking.tenant_id)
        when = _format_local_time(booking.starts_at, business)

        intent = NotificationOutbox(
            tenant_id=booking.tenant_id,
            business_id=booking.business_id,
            booking_id=booking.id,
            channel=NotificationChannel.SMS,
            purpose=NotificationPurpose.BOOKING_REMINDER,
            recipient_phone=customer.phone,
            body=f"Reminder: your {service.name} appointment at {business.name} is at {when}.",
        )
        db.add(intent)
        db.flush()
        enqueue_send_notification_job(intent.id)
        count += 1

    if count:
        db.commit()
    return count


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
    provider_name = getattr(sms_provider, "name", type(sms_provider).__name__)
    observe_sms_provider_request(
        provider=provider_name, status="success" if result.success else "failure"
    )

    intent.attempts += 1

    if result.success:
        intent.status = NotificationStatus.SENT
        intent.sent_at = datetime.now(timezone.utc)
        intent.provider_message_id = result.provider_message_id
        db.commit()
        return

    intent.last_error = result.error
    if intent.attempts >= MAX_NOTIFICATION_ATTEMPTS:
        intent.status = NotificationStatus.FAILED
        db.commit()
        return
    db.commit()
    raise SmsDeliveryError(result.error)
