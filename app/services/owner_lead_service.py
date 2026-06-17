from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.owner_lead import LeadStatus, OwnerLead
from app.services.customer_service import normalize_phone


def create_owner_lead(
    db: Session,
    *,
    business_name: str,
    owner_name: str | None,
    email: str,
    phone_number: str,
    city: str | None,
    booking_mode_interest: str,
    external_booking_url: str | None,
    message: str | None,
) -> OwnerLead:
    lead = OwnerLead(
        business_name=business_name,
        owner_name=owner_name,
        email=email.lower().strip(),
        phone_number=phone_number,
        phone_normalized=normalize_phone(phone_number),
        city=city,
        booking_mode_interest=booking_mode_interest,
        external_booking_url=external_booking_url,
        message=message,
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_owner_lead(db: Session, lead_id: int) -> OwnerLead | None:
    return db.query(OwnerLead).filter(OwnerLead.id == lead_id).first()


def require_owner_lead(db: Session, lead_id: int) -> OwnerLead:
    lead = get_owner_lead(db, lead_id)
    if lead is None:
        raise NotFoundError("Owner lead not found")
    return lead


def list_owner_leads(
    db: Session,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[OwnerLead]:
    query = db.query(OwnerLead)
    if status is not None:
        query = query.filter(OwnerLead.status == status)
    return query.order_by(OwnerLead.created_at.desc()).offset(skip).limit(limit).all()


def update_owner_lead_status(db: Session, lead_id: int, *, status: str) -> OwnerLead:
    lead = require_owner_lead(db, lead_id)
    lead.status = status
    db.commit()
    db.refresh(lead)
    return lead
