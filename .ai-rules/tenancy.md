# Tenancy Rules

Multi-tenancy is a core security boundary. Treat cross-tenant access as a
critical defect.

## Data Access

- Every query for tenant-owned data MUST filter by `tenant_id` from the
  authenticated user or resolved tenant context.
- MUST NOT load tenant-owned rows by primary key alone without a `tenant_id`
  filter.
- Tenant-owned resources include users, audit logs, uploaded files, and cached
  keys scoped per tenant.

## HTTP And JWT

- Authenticated requests MUST validate tenant membership through existing auth
  dependencies (`get_current_user`, tenant membership helpers).
- When `X-Tenant-Slug` is sent, it MUST match the JWT user's tenant.
- MUST NOT add endpoints that return data across tenants unless the user task
  explicitly requires platform-wide access and uses `platform_admin`
  permissions.

## Tests

- New tenant-scoped resources or queries MUST add or extend regression coverage
  in `tests/test_tenant_isolation.py` or `tests/test_tenancy.py`.
- Tenant or auth changes MUST run those tests before commit.
