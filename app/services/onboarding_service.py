from sqlalchemy.orm import Session

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

    Builds ORM objects directly and issues a single db.commit() at the end
    so that a failure on any item rolls back the entire setup.
    """
    biz_spec = request.business
    business = Business(
        tenant_id=tenant_id,
        name=biz_spec.name,
        timezone=biz_spec.timezone,
        phone=biz_spec.phone,
        is_active=True,
        booking_mode=biz_spec.booking_mode,
        external_booking_url=biz_spec.external_booking_url,
        external_booking_label=biz_spec.external_booking_label,
        external_booking_provider=biz_spec.external_booking_provider,
        subscription_plan=biz_spec.subscription_plan,
    )
    db.add(business)
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
