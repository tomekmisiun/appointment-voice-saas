from fastapi import Request
from sqlalchemy.orm import Session

from app.core.domain_errors import BadRequestError, NotFoundError
from app.core.tenant_context import DEFAULT_TENANT_SLUG, get_tenant_id
from app.models.audit_log import AuditAction
from app.models.tenant import Tenant
from app.services.audit_log_service import create_audit_log


def get_tenant_by_slug(db: Session, slug: str) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.slug == slug).first()


def get_tenant_by_id(db: Session, tenant_id: int) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def resolve_tenant_slug(request: Request) -> str:
    return request.headers.get("X-Tenant-Slug", DEFAULT_TENANT_SLUG)


def get_active_tenant_by_slug(db: Session, slug: str) -> Tenant:
    tenant = get_tenant_by_slug(db, slug)

    if tenant is None or not tenant.is_active:
        raise NotFoundError("Tenant not found")

    return tenant


def get_required_tenant_id() -> int:
    tenant_id = get_tenant_id()

    if tenant_id is None:
        raise BadRequestError("Tenant context is required")

    return tenant_id


def build_tenant_cache_prefix(tenant_id: int) -> str:
    return f"tenant:{tenant_id}"


def build_tenant_object_key_prefix(tenant_id: int) -> str:
    return f"tenants/{tenant_id}"


def create_tenant(db: Session, slug: str, name: str) -> Tenant:
    existing_tenant = get_tenant_by_slug(db, slug)

    if existing_tenant is not None:
        raise BadRequestError("Tenant with this slug already exists")

    tenant = Tenant(slug=slug, name=name, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def list_tenants(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
) -> list[Tenant]:
    query = db.query(Tenant)

    if not include_inactive:
        query = query.filter(Tenant.is_active.is_(True))

    return (
        query.order_by(Tenant.slug.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_tenant(
    db: Session,
    tenant_id: int,
    *,
    name: str | None = None,
    is_active: bool | None = None,
) -> Tenant | None:
    tenant = get_tenant_by_id(db, tenant_id)

    if tenant is None:
        return None

    if name is not None:
        tenant.name = name

    if is_active is not None:
        tenant.is_active = is_active

    db.commit()
    db.refresh(tenant)

    return tenant


def provision_tenant(
    db: Session,
    *,
    slug: str,
    name: str,
    admin_id: int,
    admin_tenant_id: int,
) -> Tenant:
    tenant = create_tenant(db, slug, name)
    create_audit_log(
        db,
        tenant_id=admin_tenant_id,
        admin_id=admin_id,
        action=AuditAction.TENANT_CREATED,
    )

    return tenant


def set_tenant_active_state(
    db: Session,
    *,
    tenant_id: int,
    is_active: bool,
    admin_id: int,
    admin_tenant_id: int,
) -> Tenant | None:
    tenant = update_tenant(db, tenant_id, is_active=is_active)

    if tenant is None:
        return None

    action = (
        AuditAction.TENANT_ACTIVATED
        if is_active
        else AuditAction.TENANT_DEACTIVATED
    )
    create_audit_log(
        db,
        tenant_id=admin_tenant_id,
        admin_id=admin_id,
        action=action,
    )

    return tenant
