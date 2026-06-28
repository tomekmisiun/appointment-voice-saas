# Legacy Route Deprecation Policy

The template exposes two parallel route namespaces:

- **Current:** `/api/v1/...`
- **Legacy (deprecated):** unversioned paths such as `/auth/login`, `/users/`, `/admin`

Legacy routes exist for backward compatibility during client migration. New
clients must use `/api/v1`.

## Current Behavior

- Versioned routes are mounted from `app/api/v1.py`.
- Legacy routes are mounted from `app/api/legacy.py` with `deprecated=True` when
  `LEGACY_ROUTES_ENABLED` is true.
- Default: legacy routes are **enabled** in development, test, and staging, and
  **disabled** in production (`ENVIRONMENT=production`).
- Set `LEGACY_ROUTES_ENABLED=true` explicitly only when production still needs
  unversioned paths during client migration.
- OpenAPI marks legacy operations as deprecated when they are mounted.
- Regression tests in `tests/test_api_versioning.py` cover both enabled and
  disabled behavior.

## Recommended Migration Plan

For each downstream project:

1. Inventory clients still calling unversioned paths.
2. Move new integrations to `/api/v1` immediately.
3. Announce a sunset date for legacy paths (for example 90 days).
4. Monitor legacy traffic through request logs or gateway metrics keyed by path.
5. Remove legacy route mounting only after traffic reaches zero and tests are
   updated.

## Removal Checklist (Downstream)

When you are ready to delete legacy routes from your fork:

- [ ] Confirm no production traffic on unversioned paths
- [ ] Update mobile/web clients to `/api/v1`
- [ ] Remove `legacy_api_router` from `app/main.py`
- [ ] Delete `app/api/legacy.py`
- [ ] Remove `LEGACY_ROUTE_CHECKS` from `tests/test_api_versioning.py`
- [ ] Update README API overview and OpenAPI contract tests
- [ ] Communicate breaking change in release notes

## What This Template Keeps

This repository keeps legacy routes **configurable**. They are off by default in
production to avoid doubling the protected API surface. Enable them temporarily
with `LEGACY_ROUTES_ENABLED=true` while downstream clients migrate; remove the
flag after traffic reaches zero.

## Related Documents

- `tests/test_api_versioning.py` — route availability checks
- `tests/test_openapi_contract.py` — OpenAPI contract coverage
- `README.md` — API overview
