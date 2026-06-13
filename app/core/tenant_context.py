from contextvars import ContextVar

DEFAULT_TENANT_SLUG = "default"

tenant_id_var: ContextVar[int | None] = ContextVar("tenant_id", default=None)
tenant_slug_var: ContextVar[str | None] = ContextVar("tenant_slug", default=None)


def get_tenant_id() -> int | None:
    return tenant_id_var.get()


def get_tenant_slug() -> str | None:
    return tenant_slug_var.get()


def clear_tenant_context() -> None:
    tenant_id_var.set(None)
    tenant_slug_var.set(None)
