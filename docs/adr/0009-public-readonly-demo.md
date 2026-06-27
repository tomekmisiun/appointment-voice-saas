# ADR 0009 — Public Read-Only Demo

**Status:** Accepted  
**Date:** 2026-06-27

---

## Context

VoxSlot is a portfolio SaaS product. Potential clients need to experience the
dashboard, telephony status, and booking data without creating an account.
The demo workspace shares a real phone number that may receive genuine inbound
calls from the public.

The following constraints drive this decision:

1. **No credentials in the browser.** Any approach that puts the demo password
   in JavaScript, environment variables prefixed `NEXT_PUBLIC_*`, or HTML is
   rejected.
2. **One workspace, shared number.** The demo business has a real Twilio
   number. Real callers mean real PII in the database.
3. **Permanent feature.** Future registration, payments, and provisioning must
   not weaken or remove demo access.
4. **Deny-by-default.** A developer adding a new mutation endpoint must not
   accidentally expose it to anonymous demo sessions.

---

## Decision

### Dedicated public demo user

A single `User` with `is_demo_user=True` and `role="user"` is seeded into the
demo workspace. The user has a random, unknown hashed password. Direct login is
intentionally impossible.

The user has a `BusinessMembership` scoped only to the demo business.

### `POST /api/v1/auth/demo`

A dedicated endpoint issues a short-lived JWT pair without accepting
credentials. It requires `PUBLIC_DEMO_ENABLED=true` and returns 503 if the
demo workspace is not seeded. The endpoint is rate-limited (20 req/60 s).

### `is_public_demo` JWT claim

The access token for a demo session carries `is_public_demo: true` as an
additional claim. This lets the central middleware identify demo sessions
without a database round-trip.

### Central deny-by-default middleware

`app/core/demo_guard.DemoReadOnlyMiddleware` intercepts all
POST/PUT/PATCH/DELETE requests. If the request carries a JWT with
`is_public_demo=True`, the middleware returns `403 Forbidden` with a stable
error message before routing.

Exceptions (explicit allow-list):
- `POST /api/v1/auth/demo` — session creation
- `POST /api/v1/auth/logout` — session teardown
- `POST /api/v1/auth/refresh` — token renewal

`require_non_demo_user` dependency remains on individual mutation routes as
defense-in-depth.

### PII masking

Client phone and email fields are masked server-side
(`app/api/routes/clients._mask_client`) when `current_user.is_demo_user`.
Voice session `caller_phone` is not exposed via public GET endpoints.

### Account takeover prevention

| Attack vector | Mitigation |
|---|---|
| Login with known password | Random bcrypt hash; password not known |
| Password reset → email | Silently no-ops; no token minted |
| Password reset confirm | Rejected with 403 |
| Email/password/role change | Rejected with 403 (`require_non_demo_user`) |
| Access other tenants | Token scoped to demo tenant only |
| Access other businesses | `require_demo_business_access` dependency |

---

## Threat model

| Threat | Mitigation |
|---|---|
| Attacker reads real caller PII | `_mask_client` masks phone/email; voice sessions not exposed |
| Attacker gains write access | Central middleware + per-route `require_non_demo_user` |
| Attacker resets demo password | Password reset silently skipped for `is_demo_user=True` |
| Attacker uses demo session as admin | `User.role="user"`, no admin endpoints accessible |
| Developer forgets `require_non_demo_user` | Central middleware blocks regardless |
| `is_public_demo` forged in client-built JWT | JWT is HS256 signed with server-side secret |
| New mutation endpoint added without demo guard | Central middleware covers it automatically |

---

## Alternatives considered

**Option A — Public share credentials (email + password in env)**  
Rejected: credentials would appear in frontend bundle or environment
variables visible to the browser.

**Option B — Per-route `require_non_demo_user` only (status quo before this ADR)**  
Partially accepted as defense-in-depth only. Rejected as the sole mechanism
because it requires every future developer to remember to add the dependency.
One omission breaks the guarantee.

**Option C — Separate read-only tenant with no write permissions at DB level**  
Over-engineered. Would require a second database user, schema changes, and
tenant isolation rework. The middleware approach achieves the same result with
less complexity.

---

## Consequences

**Positive:**
- Demo requires zero user interaction to start (one click).
- No credentials visible in client-side code.
- New mutation endpoints are automatically blocked for demo sessions.
- Real PII from callers is masked at the API layer.

**Negative / follow-ups:**
- The `is_public_demo` JWT claim is non-standard and must be documented for
  any future token introspection tool.
- PII masking covers clients today; if new PII-bearing endpoints are added,
  they must explicitly handle the demo case.
- The demo business uses `business.phone` for the telephony display. When
  `BusinessPhoneNumber` is implemented (TELEPHONY-T1/T2), the
  `TelephonyStatusCard` component must be updated to use the new model.

---

## References

- `.ai-rules/public-demo.md` — binding rules derived from this ADR
- `app/core/demo_guard.py` — middleware implementation
- `app/services/auth_service.py::create_demo_session`
- `tests/test_public_demo.py` — contract test suite
