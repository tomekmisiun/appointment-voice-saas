from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking import (
    BookingCancelRequest,
    BookingCreate,
    BookingOverrideCancelRequest,
    BookingOverrideCreateRequest,
    BookingRead,
    BookingRescheduleRequest,
)
from app.services.booking_service import (
    cancel_booking,
    create_booking,
    list_bookings,
    require_booking_in_business,
    reschedule_booking,
)

router = APIRouter(prefix="/businesses/{business_id}/bookings", tags=["bookings"])


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    business_id: int,
    body: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return create_booking(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        customer_id=body.customer_id,
        service_id=body.service_id,
        staff_id=body.staff_id,
        starts_at=body.starts_at,
        source=body.source,
        actor_id=current_user.id,
    )


@router.post("/override", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def override_create_booking_endpoint(
    business_id: int,
    body: BookingOverrideCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Admin override booking creation (P3-012): same conflict rules as a
    normal create (the DB-level no-overlap constraint still applies for a
    staff_id with a real conflict — this does not bypass it), but requires
    an explicit reason and is logged under a distinct audit action so
    overrides are queryable separately from regular bookings."""
    return create_booking(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        customer_id=body.customer_id,
        service_id=body.service_id,
        staff_id=body.staff_id,
        starts_at=body.starts_at,
        source=body.source,
        actor_id=current_user.id,
        override=True,
        reason=body.reason,
    )


@router.get("", response_model=list[BookingRead])
def list_bookings_endpoint(
    business_id: int,
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    staff_id: int | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return list_bookings(
        db,
        business_id,
        current_user.tenant_id,
        status=status_filter,
        staff_id=staff_id,
        skip=skip,
        limit=size,
    )


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking_endpoint(
    business_id: int,
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_booking_in_business(db, booking_id, business_id, current_user.tenant_id)


@router.post("/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking_endpoint(
    business_id: int,
    booking_id: int,
    body: BookingCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return cancel_booking(
        db,
        booking_id,
        business_id,
        current_user.tenant_id,
        reason=body.reason,
        actor_id=current_user.id,
    )


@router.post("/{booking_id}/override-cancel", response_model=BookingRead)
def override_cancel_booking_endpoint(
    business_id: int,
    booking_id: int,
    body: BookingOverrideCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Admin override cancellation (P3-012): mechanically identical to a
    normal cancel (frees the slot, offers the waitlist) but requires an
    explicit reason and is logged under a distinct audit action."""
    return cancel_booking(
        db,
        booking_id,
        business_id,
        current_user.tenant_id,
        reason=body.reason,
        actor_id=current_user.id,
        override=True,
    )


@router.post("/{booking_id}/reschedule", response_model=BookingRead)
def reschedule_booking_endpoint(
    business_id: int,
    booking_id: int,
    body: BookingRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return reschedule_booking(
        db,
        booking_id,
        business_id,
        current_user.tenant_id,
        new_starts_at=body.new_starts_at,
        reason=body.reason,
        actor_id=current_user.id,
    )
