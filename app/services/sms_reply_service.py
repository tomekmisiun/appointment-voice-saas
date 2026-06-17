from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError
from app.models.booking import Booking, BookingStatus
from app.services.booking_service import cancel_booking
from app.services.customer_service import get_customer_by_phone

_CONFIRM_KEYWORDS = {"C", "CONFIRM", "Y", "YES"}
_CANCEL_KEYWORDS = {"X", "CANCEL", "N", "NO"}


class SmsReplyIntent(StrEnum):
    CONFIRM = "confirm"
    CANCEL = "cancel"
    UNRECOGNIZED = "unrecognized"


def parse_reply_intent(body: str) -> SmsReplyIntent:
    normalized = body.strip().upper()
    if normalized in _CONFIRM_KEYWORDS:
        return SmsReplyIntent.CONFIRM
    if normalized in _CANCEL_KEYWORDS:
        return SmsReplyIntent.CANCEL
    return SmsReplyIntent.UNRECOGNIZED


def _next_confirmed_booking(db: Session, *, business_id: int, tenant_id: int, customer_id: int) -> Booking | None:
    return (
        db.query(Booking)
        .filter(
            Booking.business_id == business_id,
            Booking.tenant_id == tenant_id,
            Booking.customer_id == customer_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at > datetime.now(timezone.utc),
        )
        .order_by(Booking.starts_at.asc())
        .first()
    )


def handle_sms_reply(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    from_phone: str,
    body: str,
) -> SmsReplyIntent:
    """Parse a simple confirm/cancel SMS reply and update the customer's
    soonest upcoming confirmed booking. Idempotent: a CANCEL reply on an
    already-cancelled booking is a no-op rather than an error. CONFIRM is
    also a no-op since bookings are already confirmed at creation — it only
    acknowledges the reply was understood."""
    intent = parse_reply_intent(body)
    if intent == SmsReplyIntent.UNRECOGNIZED:
        return intent

    customer = get_customer_by_phone(
        db, business_id=business_id, tenant_id=tenant_id, phone=from_phone
    )
    if customer is None:
        return intent

    booking = _next_confirmed_booking(
        db, business_id=business_id, tenant_id=tenant_id, customer_id=customer.id
    )
    if booking is None:
        return intent

    if intent == SmsReplyIntent.CANCEL:
        try:
            cancel_booking(db, booking.id, tenant_id, reason="customer_sms_reply")
        except ConflictError:
            pass

    return intent
