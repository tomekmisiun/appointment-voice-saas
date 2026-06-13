from app.core.tenant_context import DEFAULT_TENANT_SLUG
from app.models.tenant import Tenant
from app.services.tenant_seed_service import (
    DEFAULT_TENANT_NAME,
    ensure_default_tenant,
)


def test_ensure_default_tenant_creates_default_tenant(db):
    tenant = ensure_default_tenant(db, commit=False)

    assert tenant.slug == DEFAULT_TENANT_SLUG
    assert tenant.name == DEFAULT_TENANT_NAME
    assert tenant.is_active is True
    assert tenant.id is not None


def test_ensure_default_tenant_is_idempotent(db):
    first_tenant = ensure_default_tenant(db, commit=False)
    second_tenant = ensure_default_tenant(db, commit=False)

    assert first_tenant.id == second_tenant.id

    tenant_count = db.query(Tenant).filter(Tenant.slug == DEFAULT_TENANT_SLUG).count()

    assert tenant_count == 1
