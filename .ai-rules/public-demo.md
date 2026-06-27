# Public Demo — Binding Contract

This file defines the permanent, non-negotiable rules for the VoxSlot public
demo feature. Every agent, builder, and reviewer MUST read this file when
touching auth, permissions, middleware, routers, models, seed data, or the
dashboard.

## 1. The public demo is a permanent product feature

It must not be removed, disabled by default, or weakened by future
registration, payment, subscription, or provisioning work.

## 2. The public demo user is never a platform admin

The public demo user MUST have:
- `User.role = "user"` (never "admin")
- `User.is_demo_user = True`
- A random, non-guessable hashed password (not a known credential)
- A `BusinessMembership` scoped only to the demo workspace

Any seed script or migration that sets a demo user's role to "admin" is a
security defect and must be rejected in review.

## 3. The central deny-by-default middleware must not be removed

`app/core/demo_guard.DemoReadOnlyMiddleware` blocks POST/PUT/PATCH/DELETE for
any request whose access JWT carries `is_public_demo=True`.

- It MUST be registered in `app/main.py` before the routing layer.
- It MUST NOT be replaced with per-endpoint guards only.
- `require_non_demo_user` on individual routes remains as defense-in-depth.
- A new mutating endpoint is blocked by the middleware even if the developer
  forgets to add `require_non_demo_user`.

## 4. The middleware allow-list must not grow to include business-data mutations

The only allow-listed paths are:
- `POST /api/v1/auth/demo` — demo session creation
- `POST /api/v1/auth/logout` — session teardown
- `POST /api/v1/auth/refresh` — short-lived token renewal

**Critical:** `rotate_refresh_token()` MUST carry `is_public_demo=user.is_demo_user`
when creating the new access token. Without this, the refreshed token loses the
demo claim and the middleware stops blocking mutations for the rest of the session.
See `app/services/auth_service.py::rotate_refresh_token` and
`tests/test_public_demo.py::test_demo_access_token_retains_is_public_demo_after_refresh`.

Any addition to `_DEMO_ALLOWLIST` in `demo_guard.py` that permits writing
business data is a security defect. Each allow-list entry requires an explicit
reason comment and a dedicated test.

## 5. The demo account must not be accessible via normal login

- The demo user has a random hashed password.
- `POST /auth/login` with the demo email MUST fail (password not known).
- Direct password login for the demo account is intentionally broken.

## 6. Password reset and account mutation are permanently blocked

For `is_demo_user=True`:
- Password reset request: silently no-ops (no email sent, no token minted)
- Password reset confirm: rejected with 403
- Email change: rejected with 403 (`require_non_demo_user`)
- Password change: rejected with 403 (`require_non_demo_user`)
- Role change: rejected with 403 (`require_non_demo_user`)

## 7. PII must not be returned to the public demo session

Backend responses for the demo user MUST mask or exclude:
- Client phone numbers → `"***"`
- Client email addresses → `"***@***.***"`
- Real caller phone numbers from voice sessions (not exposed via public GET)

Masking is applied server-side in the API route handler, not only in the UI.
See `app/api/routes/clients.py::_mask_client`.

## 8. Hiding a UI button is not a security control

Every restriction enforced in the frontend MUST also be enforced in the
backend. A determined user can call the API directly. The backend is the
authority; the frontend is UX only.

## 9. Tests are mandatory for every part of the demo contract

The following coverage must be maintained in `tests/test_public_demo.py`:
- Demo session creation (enabled/disabled/misconfigured)
- All read-only enforcements (mutations return 403)
- Central middleware blocks an unlisted mutation endpoint
- Normal users are NOT blocked by the middleware
- Webhooks are NOT blocked (no JWT = pass-through)
- PII masking in GET /clients

Whenever auth, permissions, middleware, models, seed data, or the dashboard
change, the demo contract tests must be reviewed and updated.

## 10. Changes to this area require a named reviewer

Any PR that modifies the following files must be reviewed against this rule:
- `app/core/demo_guard.py`
- `app/core/security.py` (token creation)
- `app/services/auth_service.py` (create_demo_session)
- `app/api/dependencies/auth.py`
- `app/seed_demo_data.py`
- `app/api/routes/auth.py` (POST /demo)
- `frontend/components/layout/AppShell.tsx`
- `frontend/app/demo/page.tsx`
- `.ai-rules/public-demo.md` (this file)
