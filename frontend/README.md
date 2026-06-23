# Appointment Voice SaaS — Owner Dashboard Frontend

Next.js (App Router) owner dashboard for the Appointment Voice SaaS backend.
This branch (`feat/frontend-foundation-auth`) ships the foundation only:
project scaffold, typed API layer, authentication, and a protected dashboard
shell. See `docs/frontend/frontend-roadmap.md` (repo root) for what ships in
later branches — most nav entries are intentionally marked "Coming soon."

## Architecture in one paragraph

The browser never talks to the FastAPI backend directly. Every backend call
happens inside Next.js server code (Server Components, Route Handlers,
Server Actions) — a Backend-for-Frontend (BFF) pattern chosen because the
backend only issues Bearer JWTs (no cookies, CORS disabled by default), and
this way the frontend never needs CORS enabled or to store tokens in
browser JS. The browser only ever holds one encrypted, HttpOnly session
cookie that this app controls. See the inline docs in `lib/auth/` for the
exact refresh/redirect flow.

## Prerequisites

- Node.js 20+ (developed against Node 26)
- pnpm (`npm install -g pnpm` if not already available — there's no
  corepack-free alternative bundled with this repo)
- The backend running locally (see repo root `README.md`): `make bootstrap`
  or `make seed-tenant seed seed-demo`, served at `http://localhost:8000`
- `uv` installed at the repo root (used by `pnpm api:generate` to run the
  backend's own OpenAPI export script)

## Setup

```bash
cd frontend
pnpm install
cp .env.example .env.local
# Generate a real session secret and put it in .env.local:
openssl rand -base64 32
```

Edit `.env.local`:

```
BACKEND_API_URL=http://localhost:8000
SESSION_SECRET=<paste the generated value>
APP_ORIGIN=http://localhost:3000
# TENANT_SLUG=acme   # optional — see .env.example; leave unset for the seeded demo tenant
```

There is **no development fallback** for `SESSION_SECRET` — the app fails
fast and loudly on startup/first use if it's missing, not valid base64, or
doesn't decode to exactly 32 bytes (AES-256 key length). Generate a fresh
one per environment; don't share it between dev and anything else.

## Running

```bash
# Terminal 1, repo root — backend
docker compose up
make seed-tenant seed seed-demo   # one-time, idempotent

# Terminal 2 — frontend
cd frontend
pnpm dev
```

Open `http://localhost:3000`. Log in with the seeded demo account:
`admin@example.local` / `devpassword123` (per repo root `README.md`).

There is no `docker-compose.yml` entry for the frontend in this branch —
it's deliberately run separately with `pnpm dev` alongside the backend's
existing Compose setup (see PR discussion: adding a Compose service is a
bigger, separately-approved change than this branch's scope).

## Typed API layer

`lib/api/schema.gen.ts` is generated from the backend's live OpenAPI schema
— not hand-written — so the frontend's types stay checked against the real
contract.

```bash
pnpm api:generate   # regenerate lib/api/openapi.json + schema.gen.ts
pnpm api:check       # regenerate into the same files, then fail if that
                     # produces an uncommitted diff (contract drift)
```

Both require the backend's own Python environment (`uv`) and a `.env` at
the repo root with `SECRET_KEY` / `DATABASE_URL` set (the same ones the
backend itself needs) — `scripts/export-openapi.py` imports the FastAPI app
to read its schema; it never starts a server or touches the database.

Run `pnpm api:check` after backend API changes land, before relying on
`schema.gen.ts` — drift means the frontend's types no longer match reality.

## Testing

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

No Playwright/E2E suite in this branch — nothing here is interactive enough
to need a browser smoke test beyond the unit/component coverage (login form,
auth failure handling, protected-route redirects, the refresh flow's
concurrency-safety, CSRF rejection, session size/secret validation,
business-selection states). Playwright lands with the bookings-read branch,
once there's an actual page to click through.

## Common problems

| Symptom | Likely cause |
|---|---|
| `BACKEND_API_URL is not set` error | Missing/empty `frontend/.env.local` |
| `SESSION_SECRET is ...` error on first request | Missing, not base64, or not exactly 32 bytes once decoded — regenerate with `openssl rand -base64 32` |
| Stuck on "Signing you back in…" | Backend isn't reachable at `BACKEND_API_URL`, or the refresh token has expired/been revoked — check backend logs; this page always resolves to `/login` or the target page within one request |
| "Multiple businesses aren't supported yet" | The signed-in tenant owns more than one active business — out of scope for this branch's dashboard, not a bug |
| "No business is configured for this account" | The signed-in tenant has zero active businesses — check backend seed data |
| `pnpm api:check` fails | The backend's OpenAPI schema changed since `lib/api/schema.gen.ts` was last regenerated — run `pnpm api:generate` and commit the result |

## Project layout

```
app/            Routes (App Router) — kept thin, composition only
components/     Generic, feature-agnostic UI (ui/) and layout chrome (layout/)
features/       Domain code by feature: auth/, dashboard/
lib/
  api/          Backend base URL, error envelope, generated types, server fetch helper
  auth/         Session cookie, CSRF, refresh flow, Server Action
  validation/   Shared zod primitives
tests/          Shared test setup, MSW mocks, cookie-store test helper
```
