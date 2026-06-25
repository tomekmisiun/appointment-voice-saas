from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.onboarding import OnboardingSetupRequest, OnboardingSetupResponse
from app.services.membership_service import (
    create_owner_membership,
    get_active_business_membership,
)
from app.services.onboarding_service import setup_business_onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post(
    "",
    response_model=OnboardingSetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="One-call business setup for self-service onboarding",
    description=(
        "Creates a business together with initial staff, services, and working "
        "hours in a single request. Requires admin role. All entities are scoped "
        "to the authenticated user's tenant."
    ),
)
def onboarding_setup(
    body: OnboardingSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> OnboardingSetupResponse:
    result = setup_business_onboarding(
        db,
        tenant_id=current_user.tenant_id,
        request=body,
    )
    # signup_salon_owner already creates the OWNER membership when the tenant
    # is self-signed up. For any other path (e.g. platform admin onboarding a
    # new business), create the membership here if one does not already exist.
    if get_active_business_membership(
        db,
        user_id=current_user.id,
        business_id=result.business_id,
        tenant_id=current_user.tenant_id,
    ) is None:
        create_owner_membership(
            db,
            user_id=current_user.id,
            business_id=result.business_id,
            tenant_id=current_user.tenant_id,
        )
        db.commit()
    return result
