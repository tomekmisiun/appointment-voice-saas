from sqlalchemy.orm import Session

from app.schemas.onboarding import OnboardingSetupRequest, OnboardingSetupResponse
from app.services.business_service import create_business
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours


def setup_business_onboarding(
    db: Session,
    *,
    tenant_id: int,
    request: OnboardingSetupRequest,
) -> OnboardingSetupResponse:
    biz = request.business
    business = create_business(
        db,
        tenant_id=tenant_id,
        name=biz.name,
        timezone=biz.timezone,
        phone=biz.phone,
        booking_mode=biz.booking_mode,
        external_booking_url=biz.external_booking_url,
        external_booking_label=biz.external_booking_label,
        external_booking_provider=biz.external_booking_provider,
        subscription_plan=biz.subscription_plan,
    )

    for staff_item in request.staff:
        create_staff(
            db,
            tenant_id=tenant_id,
            business_id=business.id,
            name=staff_item.name,
            phone=staff_item.phone,
        )

    for svc_item in request.services:
        create_service(
            db,
            tenant_id=tenant_id,
            business_id=business.id,
            name=svc_item.name,
            duration_minutes=svc_item.duration_minutes,
            price_minor_units=svc_item.price_minor_units,
            currency=svc_item.currency,
        )

    for wh_item in request.working_hours:
        create_working_hours(
            db,
            tenant_id=tenant_id,
            business_id=business.id,
            staff_id=None,
            day_of_week=wh_item.day_of_week,
            start_time=wh_item.start_time,
            end_time=wh_item.end_time,
        )

    return OnboardingSetupResponse(
        business_id=business.id,
        business_name=business.name,
        staff_count=len(request.staff),
        service_count=len(request.services),
        working_hours_count=len(request.working_hours),
    )
