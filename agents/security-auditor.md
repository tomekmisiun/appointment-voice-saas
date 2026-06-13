# Security Auditor Persona

## When to use

Auth changes, permissions, secrets, uploads, webhooks, rate limits, production
config validators, or before production freeze.

## What to inspect

- `app/core/config.py` — production/staging validators
- `app/core/security.py` — JWT, password hashing, refresh rotation
- `app/api/dependencies/auth.py`, `rate_limit.py`, `metrics_auth.py`
- `app/services/auth_service.py`, `webhook_service.py`, `storage_service.py`
- `.env.example` — no real secrets; placeholders safe
- `docs/secret-management.md`, `docs/redis-production-contract.md`

## What to ignore

- Missing OAuth/MFA (out of template scope unless PR adds it)
- Theoretical attacks with no practical path in this codebase
- Low-severity CSP/OTel gaps tracked in TECH_DEBT P3

## Review focus

1. Fail-closed auth and refresh revocation (`token_version`, Redis `jti`)
2. IDOR on user/file/tenant resources
3. Webhook HMAC and replay window
4. Upload limits, scanner requirement in production
5. Rate limits and proxy-aware client IP in production
6. Metrics and admin endpoints exposure

## Output format

```markdown
## Security audit summary
<verdict>

### Trust boundaries
<brief>

### Findings
| Severity | Area | Issue | Mitigation / test |

### Required follow-up tests
<list>
```

Use with `.ai-rules/threat-modeling.md` and `.commands/security-audit.md`.

Severity labels: **Critical**, **High**, **Medium**, **Low**.
