# Public Demo Dashboard

VoxSlot ships a public read-only demo mode that lets visitors explore the
dashboard without registering. The demo user sees live data from a configured
business; all write operations are blocked server-side.

## How it works

1. Visitor clicks **Try demo** on the login page → navigates to `/demo`.
2. The Next.js page calls `POST /api/auth/demo` (BFF route handler).
3. The BFF calls `POST /api/v1/auth/demo` on the FastAPI backend.
4. The backend issues a normal JWT pair for the pre-seeded demo user.
5. Tokens are stored in the encrypted server-side session cookie (never exposed
   to the browser).
6. The browser is hard-navigated to `/dashboard`, where a yellow
   **"Public demo — read only"** banner is shown.
7. Clicking **Log out** calls `POST /api/auth/logout`, revokes the backend
   refresh token on a best-effort basis, clears the encrypted session cookie,
   and returns the browser to the public landing page.

Any attempt by the demo user to call a mutation endpoint returns
`403 Forbidden` — enforced by the `require_non_demo_user` FastAPI dependency
added to every write route.

## Configuration

Set these environment variables on the backend (Railway / `.env.local`):

| Variable | Required | Description |
|---|---|---|
| `PUBLIC_DEMO_ENABLED` | yes | `true` to activate the demo endpoint |
| `PUBLIC_DEMO_USER_EMAIL` | yes | Email of the seeded demo user |
| `PUBLIC_DEMO_BUSINESS_ID` | yes | Primary key of the business the demo user may view |
| `AUTH_DEMO_RATE_LIMIT_LIMIT` | no | Requests allowed per window (default 20) |
| `AUTH_DEMO_RATE_LIMIT_WINDOW_SECONDS` | no | Rate-limit window in seconds (default 60) |
| `TWILIO_VOICE_NUMBER` | yes for production demo calls | Booking Assistant inbound number seeded into the demo business; production demo uses `+18174057514` |
| `TWILIO_SMS_FROM` | yes for production SMS | Outbound SMS sender; production demo uses the alphanumeric Sender ID `VoxSlot` |

All three required variables must be non-empty / non-zero or `POST /api/v1/auth/demo`
returns `503 Service Unavailable`.

## Seeding the demo user

Run the seed script once per environment (idempotent — safe to re-run):

```bash
docker compose run --rm api python seed_demo_data.py
```

The script creates a `User` record with:

- `email` = value of `PUBLIC_DEMO_USER_EMAIL`
- `is_demo_user = True`
- `is_active = True`
- `role = "user"`
- A random hashed password (login via credentials is intentionally impossible)

Re-running when the user already exists is a no-op.

The same seed also synchronizes the demo business phone roles:

| Role | Stored in | Production demo value |
|---|---|---|
| Voice number / Booking Assistant | `businesses.phone` from `TWILIO_VOICE_NUMBER` or the built-in demo default | `+18174057514` |
| Owner notification number | `businesses.owner_notification_phone` | `+48505460409` |
| SMS sender ID | `TWILIO_SMS_FROM` in the API/worker environment | `VoxSlot` |

The public dashboard reads the Voice number and owner-notification status from
the backend business record. It displays the Voice number as
`+1 (817) 405-7514`, copies `+18174057514`, and masks the owner notification
number for demo visitors.

## Security design

- The backend endpoint accepts **no client-supplied credentials or IDs**; all
  lookups use server-side config only.
- The endpoint returns `503` (not `404`/`401`) when misconfigured, to avoid
  leaking information about the configuration state.
- Mutation blocking is enforced on the backend via `require_non_demo_user` — the
  frontend banner is cosmetic only.
- The demo user is scoped to a single business: `list_businesses` filters to
  `PUBLIC_DEMO_BUSINESS_ID` when `is_demo_user=True`.
- Webhook routes (`/twilio/*`, `/webhooks/*`) and IVR simulation routes are not
  protected because they use different auth mechanisms and don't expose
  user-owned data writes.
- The BFF `/api/auth/demo` route has no CSRF guard because it creates no
  user-owned state and is rate-limited on the backend.

## Rate limiting

`POST /api/v1/auth/demo` shares the Redis-based sliding-window rate limiter used
by other auth endpoints. Default: 20 requests per 60 seconds per IP.

## Disabling the demo

Set `PUBLIC_DEMO_ENABLED=false` (or remove the variable). The backend will
return `503` for all demo login attempts; the frontend `/demo` page will display
the error message and a link back to sign in.
