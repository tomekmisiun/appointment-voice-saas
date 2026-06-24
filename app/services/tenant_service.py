import re

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.domain_errors import BadRequestError, NotFoundError
from app.core.tenant_context import DEFAULT_TENANT_SLUG, get_tenant_id
from app.models.audit_log import AuditAction
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.audit_log_service import create_audit_log

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")


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


def _slugify(name: str) -> str:
    slug = _SLUG_INVALID_CHARS.sub("-", name.strip().lower()).strip("-")
    return slug or "salon"


def _unique_slug(db: Session, base_slug: str) -> str:
    """Append -2, -3, ... until a free slug is found. Bounded loop, not
    unbounded recursion -- a public signup endpoint must not be able to
    spin forever even under a pathological flood of identical salon_name
    values."""
    if get_tenant_by_slug(db, base_slug) is None:
        return base_slug
    for suffix in range(2, 1000):
        candidate = f"{base_slug}-{suffix}"
        if get_tenant_by_slug(db, candidate) is None:
            return candidate
    raise BadRequestError("Could not generate a unique slug, please provide one explicitly")


def signup_tenant(
    db: Session,
    *,
    salon_name: str,
    slug: str | None,
    admin_email: str,
    admin_password: str,
) -> tuple[Tenant, User]:
    """Public self-service signup (P4-004): a new salon owner provisions
    their own tenant and admin account, with no manually-created tenant or
    platform-admin action required first -- the gap `provision_tenant()`
    (admin-only, `POST /admin/tenants`) deliberately does not fill, since
    that endpoint exists for an already-onboarded platform admin to create
    *another* tenant, not for the public to create their own first one.

    Resolves `slug` if not explicitly provided (auto-generated from
    `salon_name`, de-duplicated with a numeric suffix), then creates the
    tenant and a single admin-role user in it -- admin, not the default
    "user" role, since they need to immediately manage their own business
    (staff/services/hours) via the existing `POST /api/v1/onboarding` flow,
    which is unchanged by this function and not called from here."""
    from app.services.auth_service import create_user  # local: avoids a
    # module-load-time circular import (auth_service -> user_service ->
    # tenant_service), since this function is the only thing in
    # tenant_service.py that needs auth_service at all.

    resolved_slug = slug or _unique_slug(db, _slugify(salon_name))
    tenant = create_tenant(db, resolved_slug, salon_name)

    user = create_user(
        db,
        UserCreate(email=admin_email, password=admin_password),
        tenant.id,
        role="admin",
    )

    create_audit_log(
        db,
        tenant_id=tenant.id,
        admin_id=None,
        action=AuditAction.TENANT_CREATED,
        source="self_signup",
    )

    return tenant, user


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
