from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.tenant_context import tenant_id_var, tenant_slug_var
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.tenant_service import get_active_tenant_by_slug, resolve_tenant_slug


def get_request_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = get_active_tenant_by_slug(db, resolve_tenant_slug(request))
    tenant_id_var.set(tenant.id)
    tenant_slug_var.set(tenant.slug)
    request.state.tenant_id = tenant.id
    request.state.tenant_slug = tenant.slug

    return tenant
