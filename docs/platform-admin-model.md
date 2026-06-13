# Platform Admin Model

How `platform_admin` works in this template, what it is **not**, and how forks
should evolve operator access for production.

## What The Template Implements Today

`platform_admin` is a **role string on a normal `users` row**. Platform
operators are tenant members like any other account:

- Each user has `users.tenant_id` (single-tenant membership).
- JWT access tokens include `tenant_id` from that row.
- Permission checks use `require_permission(...)` against static role maps in
  `app/core/permissions.py`.

Platform operators receive `tenants.list`, `tenants.provision`, and
`tenants.manage` in addition to tenant-scoped admin permissions (`users.*`,
`audit_logs.list`, and so on).

Tenant lifecycle APIs live under `/api/v1/admin/tenants` and are gated by those
permissions. Listing and mutating **customer tenants** does not require the
operator's JWT to impersonate those tenants — the routes query the global
`tenants` table directly when the caller has `tenants.*` permissions.

## Demo-Only Boundary (Template Scope)

The seeded dev account `admin@example.local` (`platform_admin` in the `default`
tenant) exists to **exercise tenant lifecycle APIs locally**. It is not a
production operator model.

Before production traffic:

1. Remove or replace dev seed accounts (`app/seed_dev_data.py`).
2. Decide how real operators authenticate (separate IdP group, internal SSO,
   break-glass accounts, and so on).
3. Document who may hold `platform_admin` and how those accounts are provisioned.
4. Do **not** treat “platform operator = user row in the default tenant” as a
   finished security design.

The template intentionally keeps the implementation small so forks can choose
their own operator boundary without inheriting the wrong abstraction.

## Behavioral Details Forks Should Know

### Tenant context on operator requests

Authenticated requests still carry the operator's home `tenant_id` in the JWT.
Tenant-scoped admin routes (`/api/v1/admin`, `/api/v1/users`, file routes, and
so on) operate on **that** tenant unless you add fork-specific cross-tenant
machinery.

Only `tenants.*` permissions unlock global tenant lifecycle reads and writes.

### Audit logs for lifecycle actions

`provision_tenant()` and `set_tenant_active_state()` write audit events to the
**operator's tenant** (`admin_tenant_id`), not the tenant being created or
deactivated. That matches “platform team actions recorded in the platform
tenant,” but forks may want a dedicated operator audit stream.

### Role hierarchy

`platform_admin` satisfies checks for `admin` and `user` roles via
`role_includes()` in `app/core/permissions.py`. A platform operator can perform
tenant-admin actions within their home tenant without a separate `admin` role
assignment.

## Production Options For Forks

Choose one path explicitly in your runbook. Mixing models without documentation
is a common source of privilege bugs.

### Option A — Keep role on a dedicated platform tenant (minimal change)

- Create a non-customer tenant (for example `platform`) for operator accounts.
- Assign `platform_admin` only to users in that tenant.
- Disable public registration into the platform tenant.
- Use separate credentials and MFA policy for operator accounts.

**Pros:** Smallest diff from the template; existing tests and routes still apply.

**Cons:** Operators remain indistinguishable from customer users at the schema
level; harder to attach operator-only MFA, IP allowlists, or session policy.

### Option B — Separate operator table (recommended for production SaaS)

Introduce an `operators` (or `staff_users`) table that is **not** tenant-scoped:

| Concern | Customer `users` | Operators |
|---------|------------------|-----------|
| Primary key | `users.id` | `operators.id` |
| Tenant membership | required (`tenant_id`) | none or optional home tenant |
| Auth issuer | tenant JWT | separate issuer/claims or auth dependency |
| Permissions | tenant RBAC | operator RBAC (`tenants.*`, support tools) |

Implementation sketch:

1. Add `operators` model and migration.
2. Split auth dependencies: `get_current_user` vs `get_current_operator`.
3. Mount tenant lifecycle routes on operator dependencies only.
4. Migrate dev seed to create an operator row instead of `platform_admin` user.
5. Extend `tests/test_tenant_isolation.py` with operator-only lifecycle coverage.

**Pros:** Clear security boundary; operator sessions can use stricter policy.

**Cons:** Fork-owned migration and auth work; template will not ship this by
default without a major version bump.

### Option C — External identity provider for operators

- Keep customer auth in the template's JWT flow.
- Protect `/api/v1/admin/tenants` behind an API gateway or internal service that
  validates corporate SSO (OIDC/SAML).
- Map IdP groups to `tenants.*` permissions at the gateway or via a thin
  operator-auth middleware.

**Pros:** Aligns with enterprise security teams; no operator passwords in app DB.

**Cons:** Infrastructure-specific; harder to reproduce in local Compose without
mock IdP.

## Security Checklist Before Go-Live

- [ ] Dev `platform_admin` seed removed or rotated in non-local environments.
- [ ] Operator provisioning documented (who creates accounts, approval flow).
- [ ] Break-glass and offboarding procedures defined.
- [ ] Audit destination for lifecycle actions reviewed (platform tenant vs
  central operator log).
- [ ] Rate limits and auth lockout policy applied to operator login endpoints.
- [ ] Cross-tenant data access tested — customer tokens must not call
  `tenants.*` routes (see `tests/test_tenant_isolation.py`).

## Related Docs

- `docs/tenant-isolation.md` — request boundaries and role summary
- `docs/template-onboarding.md` — rename dev seeds and production checklist
- `app/core/permissions.py` — role-to-permission maps
- `tests/test_tenant_isolation.py` — lifecycle and denial regression tests
