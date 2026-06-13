from sqlalchemy.orm import Session

from app.core.tenant_context import DEFAULT_TENANT_SLUG
from app.models.tenant import Tenant
from app.services.tenant_service import get_tenant_by_slug


DEFAULT_TENANT_NAME = "Default Tenant"


def ensure_default_tenant(db: Session, *, commit: bool = True) -> Tenant:
    tenant = get_tenant_by_slug(db, DEFAULT_TENANT_SLUG)

    if tenant is not None:
        return tenant

    tenant = Tenant(
        slug=DEFAULT_TENANT_SLUG,
        name=DEFAULT_TENANT_NAME,
        is_active=True,
    )
    db.add(tenant)

    if commit:
        db.commit()
        db.refresh(tenant)
    else:
        db.flush()

    return tenant
