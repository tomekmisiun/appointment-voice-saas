from app.core.tenant_context import (
    clear_tenant_context,
    tenant_id_var,
    tenant_slug_var,
)


def test_clear_tenant_context_resets_values():
    tenant_id_var.set(42)
    tenant_slug_var.set("acme")

    clear_tenant_context()

    assert tenant_id_var.get() is None
    assert tenant_slug_var.get() is None
