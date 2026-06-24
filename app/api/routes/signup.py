from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.rate_limit import tenant_signup_rate_limit
from app.core.config import settings
from app.db.session import get_db
from app.schemas.signup import TenantSignupRequest, TenantSignupResponse
from app.services.tenant_service import signup_tenant

router = APIRouter(tags=["signup"])


@router.post(
    "/signup",
    response_model=TenantSignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Self-service salon signup",
    description=(
        "Public endpoint — no authentication required. Creates a brand new "
        "tenant and its first admin user in one call; no manually-created "
        "tenant or platform-admin action needed first. Rate-limited per IP."
    ),
    dependencies=[Depends(tenant_signup_rate_limit())],
)
def signup(
    body: TenantSignupRequest,
    db: Session = Depends(get_db),
):
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    tenant, user = signup_tenant(
        db,
        salon_name=body.salon_name,
        slug=body.slug,
        admin_email=str(body.admin_email),
        admin_password=body.admin_password,
    )
    return TenantSignupResponse(tenant=tenant, user=user)
