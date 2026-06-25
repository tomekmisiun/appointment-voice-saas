from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog
from app.models.business import Business
from app.models.service import Service
from app.models.staff import Staff
from app.models.working_hours import WorkingHours
from app.schemas.onboarding import OnboardingSetupRequest, OnboardingSetupResponse


def setup_business_onboarding(
    db: Session,
    *,
    tenant_id: int,
    request: OnboardingSetupRequest,
) -> OnboardingSetupResponse:
    """Create business + staff + services + working hours in one transaction.

    Reuses the empty Business created by self-service signup when present;
    otherwise builds ORM objects directly and issues a single db.commit() at
    the end so that a failure on any item rolls back the entire setup.
    """
    biz_spec = request.business
    business = _get_reusable_signup_business(db, tenant_id)

    if business is None:
        business = Business(tenant_id=tenant_id)
        db.add(business)

    business.name = biz_spec.name
    business.timezone = biz_spec.timezone
    business.phone = biz_spec.phone
    business.is_active = True
    business.booking_mode = biz_spec.booking_mode
    business.external_booking_url = biz_spec.external_booking_url
    business.external_booking_label = biz_spec.external_booking_label
    business.external_booking_provider = biz_spec.external_booking_provider
    business.subscription_plan = biz_spec.subscription_plan
    db.flush()  # get business.id before adding dependents

    for item in request.staff:
        db.add(Staff(
            tenant_id=tenant_id,
            business_id=business.id,
            name=item.name,
            phone=item.phone,
            is_active=True,
        ))

    for item in request.services:
        db.add(Service(
            tenant_id=tenant_id,
            business_id=business.id,
            name=item.name,
            duration_minutes=item.duration_minutes,
            is_active=True,
            price_minor_units=item.price_minor_units,
            currency=item.currency,
        ))

    for item in request.working_hours:
        db.add(WorkingHours(
            tenant_id=tenant_id,
            business_id=business.id,
            staff_id=None,
            day_of_week=item.day_of_week,
            start_time=item.start_time,
            end_time=item.end_time,
        ))

    db.commit()
    db.refresh(business)

    return OnboardingSetupResponse(
        business_id=business.id,
        business_name=business.name,
        staff_count=len(request.staff),
        service_count=len(request.services),
        working_hours_count=len(request.working_hours),
    )


def _get_reusable_signup_business(db: Session, tenant_id: int) -> Business | None:
    self_signup_audit = (
        db.query(AuditLog.id)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == AuditAction.TENANT_CREATED,
            AuditLog.source == "self_signup",
        )
        .first()
    )
    if self_signup_audit is None:
        return None

    businesses = db.query(Business).filter(Business.tenant_id == tenant_id).all()
    if len(businesses) != 1:
        return None

    business = businesses[0]
    has_dependents = any((
        db.query(Staff.id).filter(Staff.business_id == business.id).first(),
        db.query(Service.id).filter(Service.business_id == business.id).first(),
        db.query(WorkingHours.id).filter(WorkingHours.business_id == business.id).first(),
    ))
    return None if has_dependents else business
