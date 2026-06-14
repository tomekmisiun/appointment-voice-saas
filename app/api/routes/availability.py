from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.availability import AvailabilitySlot
from app.services.availability_service import get_available_slots

router = APIRouter(prefix="/businesses/{business_id}", tags=["availability"])


@router.get("/availability", response_model=list[AvailabilitySlot])
def get_availability(
    business_id: int,
    service_id: int = Query(...),
    query_date: date = Query(..., alias="date"),
    staff_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slots = get_available_slots(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        service_id=service_id,
        staff_id=staff_id,
        query_date=query_date,
    )
    return [AvailabilitySlot(starts_at=starts, ends_at=ends) for starts, ends in slots]
