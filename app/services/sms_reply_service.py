from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError
from app.models.audit_log import AuditAction
from app.services.audit_log_service import create_audit_log
from app.services.booking_service import cancel_booking, get_next_confirmed_booking
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
    already-cancelled booking is a no-op rather than an error. CONFIRM
    doesn't change booking state (bookings are already confirmed at
    creation) but does log a BOOKING_CONFIRMED audit entry as proof the
    customer engaged with the reminder."""
    intent = parse_reply_intent(body)
    if intent == SmsReplyIntent.UNRECOGNIZED:
        return intent

    customer = get_customer_by_phone(
        db, business_id=business_id, tenant_id=tenant_id, phone=from_phone
    )
    if customer is None:
        return intent

    booking = get_next_confirmed_booking(
        db, business_id=business_id, tenant_id=tenant_id, customer_id=customer.id
    )
    if booking is None:
        return intent

    if intent == SmsReplyIntent.CANCEL:
        try:
            cancel_booking(db, booking.id, business_id, tenant_id, reason="customer_sms_reply")
        except ConflictError:
            pass
    elif intent == SmsReplyIntent.CONFIRM:
        create_audit_log(
            db,
            tenant_id=tenant_id,
            admin_id=None,
            action=AuditAction.BOOKING_CONFIRMED,
            target_booking_id=booking.id,
            source="sms_reply",
        )

    return intent
