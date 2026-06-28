# Tenant Isolation

This template uses single-tenant membership per user account. Each user row
belongs to exactly one tenant through `users.tenant_id`, and all tenant-scoped
data paths validate that membership before returning or mutating data.

## Request Boundaries

Tenant context is resolved in two places:

- Public auth flows resolve the tenant from `X-Tenant-Slug` (default: `default`).
- Authenticated requests validate JWT `tenant_id` against the loaded user row.

When an authenticated request includes `X-Tenant-Slug`, the header must match
the user's tenant. A mismatch returns `403 Tenant access denied` even if the
JWT is otherwise valid.

Inactive tenants are rejected for authenticated access and refresh-token
rotation.

## Authorization Layers

Tenant isolation is enforced at multiple layers:

1. JWT claims include `tenant_id` and are validated on every authenticated
   request.
2. Service helpers such as `users_share_tenant()` deny cross-tenant reads and
   updates.
3. Storage, audit logs, cache keys, and object keys are namespaced by tenant.
4. Admin tenant provisioning endpoints require explicit tenant-management
   permissions.

## Default Tenant Provisioning

The `default` tenant is provisioned through two complementary, idempotent paths:

1. **Migration backfill (upgrade safety)** — revision
   `a1b2c3d4e5f6_add_multi_tenancy_foundation` inserts the `default` tenant only
   when no row with `slug = 'default'` exists, then backfills `tenant_id` on
   existing users. This keeps databases that applied earlier revisions consistent
   without assuming a fixed numeric tenant id (`Identity` assigns ids).
2. **Application seed (canonical for fresh installs)** — `ensure_default_tenant()`
   in `app/services/tenant_seed_service.py`, invoked by `make seed-tenant`,
   `make bootstrap`, test fixtures, and dev seed scripts.

For new environments, run `make seed-tenant` (or `make bootstrap`) after
migrations. The migration insert remains intentional so upgrades from pre-tenant
schemas never end up with users lacking a tenant row.

## Provisioning Lifecycle

Recommended lifecycle for new tenants:

1. Provision the tenant with `POST /api/v1/admin/tenants`.
2. Share the tenant slug with the customer application.
3. Register or invite users through `/api/v1/auth/register` with
   `X-Tenant-Slug: <tenant-slug>` when `REGISTRATION_POLICY=public`.
4. Deactivate the tenant with `PATCH /api/v1/admin/tenants/{tenant_id}` when
   the customer offboards.

Provisioning and lifecycle changes are audit logged in the provisioning
admin's tenant audit stream.

## Platform Admin vs Tenant Admin

The template distinguishes two admin roles:

- `admin` — tenant admin. Manages users, audit logs, and files within the
  user's own tenant only.
- `platform_admin` — platform operator. Includes all tenant-admin permissions
  plus global tenant lifecycle permissions (`tenants.*`).

Tenant lifecycle endpoints require `platform_admin` (or any role with
`tenants.*` permissions):

- `tenants.list` for listing and reading tenants
- `tenants.provision` for creating tenants
- `tenants.manage` for activation/deactivation and metadata updates

Regular `user` role accounts cannot access tenant lifecycle endpoints. Tenant
`admin` accounts in customer tenants are denied tenant lifecycle access.

Provision platform operators in the seeded `default` tenant (or your chosen
platform tenant) with role `platform_admin`.

**Production note:** The template treats this as a **demo convenience**, not a
finished operator security model. See `docs/platform-admin-model.md` for fork
decision paths (dedicated platform tenant, separate operator table, or external
IdP).

## Admin Permissions

Tenant admins receive tenant-scoped permissions such as `users.*`,
`admin.access`, and `audit_logs.list`, but not `tenants.*`.

## Regression Expectations

When extending tenant-aware features, keep these guarantees:

- Cross-tenant user reads and updates must return `403` or `404`.
- Tokens issued for one tenant must not authorize actions in another tenant.
- Deactivated tenants must not authenticate or refresh tokens successfully.
- Cache and object storage prefixes must remain tenant-scoped.

Add integration tests under `tests/test_tenant_isolation.py` when changing
tenant authorization paths.
