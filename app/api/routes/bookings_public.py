"""Public booking management endpoints — no auth required, HMAC token enforces access.

Routes:
  GET  /api/v1/bookings/public/{token}            — fetch booking summary
  POST /api/v1/bookings/public/{token}/cancel     — customer self-cancel
  POST /api/v1/bookings/public/{token}/reschedule — customer self-reschedule
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError
from app.db.session import get_db
from app.models.booking import BookingStatus
from app.schemas.booking import BookingCancelRequest, BookingPublicRead, BookingRescheduleRequest
from app.services.booking_public_service import get_booking_by_public_token
from app.services.booking_service import cancel_booking, reschedule_booking

router = APIRouter(prefix="/bookings/public", tags=["bookings-public"])


@router.get("/{token}", response_model=BookingPublicRead)
def get_public_booking(token: str, db: Session = Depends(get_db)):
    """Return the booking identified by the HMAC token.

    404 if the token is invalid, forged, or the booking does not exist.
    """
    return get_booking_by_public_token(db, token)


@router.post(
    "/{token}/cancel",
    response_model=BookingPublicRead,
    status_code=status.HTTP_200_OK,
)
def cancel_public_booking(
    token: str,
    body: BookingCancelRequest,
    db: Session = Depends(get_db),
):
    """Customer self-cancel via public link.

    Only cancels confirmed bookings; raises 409 for already-cancelled.
    """
    booking = get_booking_by_public_token(db, token)

    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError("This booking is already cancelled.")

    return cancel_booking(
        db,
        booking.id,
        booking.business_id,
        booking.tenant_id,
        reason=body.reason or "Customer cancelled via link",
        actor_id=None,
    )


@router.post(
    "/{token}/reschedule",
    response_model=BookingPublicRead,
    status_code=status.HTTP_200_OK,
)
def reschedule_public_booking(
    token: str,
    body: BookingRescheduleRequest,
    db: Session = Depends(get_db),
):
    """Customer self-reschedule via public link."""
    booking = get_booking_by_public_token(db, token)

    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError("Cannot reschedule a cancelled booking.")

    return reschedule_booking(
        db,
        booking.id,
        booking.business_id,
        booking.tenant_id,
        new_starts_at=body.new_starts_at,
        reason=body.reason or "Customer rescheduled via link",
        actor_id=None,
    )
