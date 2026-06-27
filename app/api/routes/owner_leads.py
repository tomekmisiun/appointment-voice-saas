from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_non_demo_user, require_role
from app.api.dependencies.rate_limit import rate_limit
from app.db.session import get_db
from app.models.owner_lead import LeadStatus
from app.models.user import User
from app.schemas.owner_lead import (
    OwnerLeadAdminRead,
    OwnerLeadCreate,
    OwnerLeadPublicRead,
    OwnerLeadStatusUpdate,
)
from app.services.owner_lead_service import (
    create_owner_lead,
    list_owner_leads,
    require_owner_lead,
    update_owner_lead_status,
)

router = APIRouter(prefix="/owner-leads", tags=["owner-leads"])

_PUBLIC_RATE_LIMIT = rate_limit(limit=5, window_seconds=3600, key_prefix="rate_limit:owner_lead")


@router.post(
    "",
    response_model=OwnerLeadPublicRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a pilot interest lead",
    description=(
        "Public endpoint — no authentication required. "
        "Rate-limited to 5 submissions per IP per hour."
    ),
    dependencies=[Depends(_PUBLIC_RATE_LIMIT)],
)
def submit_owner_lead(
    body: OwnerLeadCreate,
    db: Session = Depends(get_db),
):
    lead = create_owner_lead(
        db,
        business_name=body.business_name,
        owner_name=body.owner_name,
        email=str(body.email),
        phone_number=body.phone_number,
        city=body.city,
        booking_mode_interest=body.booking_mode_interest,
        external_booking_url=body.external_booking_url,
        message=body.message,
    )
    return lead


@router.get(
    "",
    response_model=list[OwnerLeadAdminRead],
    summary="List pilot interest leads (admin)",
    dependencies=[],
)
def list_leads(
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    skip = (page - 1) * size
    return list_owner_leads(db, status=status_filter, skip=skip, limit=size)


@router.get(
    "/{lead_id}",
    response_model=OwnerLeadAdminRead,
    summary="Get a single pilot lead (admin)",
)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return require_owner_lead(db, lead_id)


@router.patch(
    "/{lead_id}/status",
    response_model=OwnerLeadAdminRead,
    summary="Update lead status (admin)",
    dependencies=[Depends(require_non_demo_user)],
)
def patch_lead_status(
    lead_id: int,
    body: OwnerLeadStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return update_owner_lead_status(db, lead_id, status=body.status)
