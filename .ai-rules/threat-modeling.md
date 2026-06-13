# Threat Modeling

Required for changes touching **auth, permissions, tenant-owned data, uploads,
webhooks, queues, workers, external integrations**, or agent-controlled flows
that mutate production data.

Complements `.ai-rules/security.md` and `.ai-rules/tenancy.md`.

## Mini threat model template

1. **Change summary** — what is being added or altered?
2. **Trust boundaries** — client → API → DB/Redis/S3/worker/SMTP/scanner
3. **Assets at risk** — credentials, PII, tenant data, files, queue jobs
4. **Actors** — anonymous, authenticated user, tenant admin, platform admin,
   worker, external webhook sender
5. **Abuse cases** — list concrete attacks (IDOR, cross-tenant read, token replay,
   webhook replay, upload malware, rate-limit bypass, job poisoning)
6. **Mitigations** — existing or new controls (permissions, validation, rate
   limits, HMAC, idempotency, scanner, fail-closed Redis)
7. **Required tests** — map each abuse case to a test or explicit gap
8. **Validation** — `make validate` + targeted security/tenancy tests

## Repo-specific hotspots

| Area | Inspect |
|------|---------|
| Auth | `app/services/auth_service.py`, `app/api/dependencies/auth.py`, refresh rotation |
| Admin | `require_permission`, role enum, audit logs |
| Tenancy | `tenant_id` filters, `X-Tenant-Slug` vs JWT |
| Uploads | size/type/magic bytes, malware scanner URL in production |
| Webhooks | HMAC, timestamp window, body size, rate limits |
| Workers | unknown job → DLQ, idempotency, maintenance locks |
| Metrics | bearer auth in production |

## Severity for findings

| Label | Meaning |
|-------|---------|
| Critical | Exploitable without auth or cross-tenant data leak |
| High | Auth bypass, privilege escalation, secret exposure |
| Medium | Missing rate limit, weak validation, DoS vector |
| Low | Hardening, defense in depth, doc gap |

Use `.commands/security-audit.md` for a full-repo or diff-scoped audit prompt.
