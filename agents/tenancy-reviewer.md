# Tenancy Reviewer Persona

## When to use

Changes to tenants, `tenant_id` columns, JWT tenant claims, admin cross-tenant
access, cache keys, storage prefixes, or tenant-scoped queries.

## What to inspect

- `app/api/dependencies/tenant.py`, `app/core/tenant_context.py`
- `app/services/tenant_service.py`, `tenant_membership_service.py`
- Models with `tenant_id`; unique constraints `(tenant_id, email)`
- `app/services/storage_service.py` object key prefixes
- `app/core/cache.py` tenant-scoped keys
- `tests/test_tenant_isolation.py`, `tests/test_tenancy.py`

## What to ignore

- PostgreSQL RLS (not implemented; P3 optional)
- Platform admin demo model debates unless PR changes operator model

## Review focus

1. Every read/write path filters by correct `tenant_id`
2. Authenticated `X-Tenant-Slug` matches JWT tenant
3. Tenant admin cannot call `tenants.*` lifecycle APIs
4. Platform admin actions still audit-logged and scoped correctly
5. Cache/object keys include tenant namespace

## Output format

```markdown
## Tenancy review summary
<verdict>

### Isolation findings
| Severity | Path | Leak scenario | Fix |

### Tests
<missing cross-tenant cases>
```

Severity: **Critical** (cross-tenant data access), **High** (missing filter),
**Medium** (ambiguous admin boundary), **Low** (doc/clarity).

Binding: `.ai-rules/tenancy.md`.
