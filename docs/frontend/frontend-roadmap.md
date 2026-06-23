# Frontend Roadmap

Executable, branch-sized backlog for the Appointment Voice SaaS owner
dashboard frontend (`frontend/`). One task = one branch = one PR. Do not
combine tasks across rows into a single branch.

Each task defines: Goal, Scope, Out of scope, Backend dependencies,
Acceptance, Tests, Risks — same field discipline as
`docs/appointment-saas-roadmap.md`.

The original single "frontend foundation / bookings / cancellation" task
was split into four narrower branches (1a–1d) during review of the first
branch's plan, so no single PR bundles authentication, a real data module,
and a destructive action together.

## 1a. Frontend foundation and authentication

| Field | Detail |
|---|---|
| Status | **Done** — `feat/frontend-foundation-auth` |
| Branch | `feat/frontend-foundation-auth` |
| Goal | Stand up the Next.js app, a typed API layer checked against the live backend OpenAPI schema, BFF authentication (login/logout/refresh), and a protected dashboard shell. |
| Scope | Next.js (App Router) + TypeScript strict scaffold; `scripts/export-openapi.py` + `pnpm api:generate`/`api:check`; encrypted HttpOnly session cookie (`lib/auth/session.ts`) with strict `SESSION_SECRET` validation; login/logout Route Handlers with Origin/Referer CSRF checks; refresh flow (Server Component → Server Action, never a GET handler that mutates); dashboard layout enforcing auth and branching on 0/1/2+ active businesses; sidebar/header/mobile nav with every non-Overview entry marked "Coming soon"; Overview page using only real business/staff/services/working-hours data. |
| Out of scope | Bookings list/detail/cancel/reschedule, every other nav module, React Query, Playwright (nothing interactive enough yet to justify either), Compose changes, backend changes. |
| Backend dependencies | `/api/v1/auth/{login,logout,refresh,me}`, `/api/v1/businesses`. No gaps found for this task's scope. |
| Acceptance | Unauthenticated users cannot reach `/dashboard/*`; login works against the real backend contract; logout clears the session and revokes the refresh token server-side; 0/1/2+ active-business states each render correctly with no implicit `businesses[0]` pick; `pnpm build` succeeds; TypeScript strict passes. |
| Tests | Login form validation/failure; CSRF accept/reject; session encrypt/decrypt round-trip + size guardrail + secret-validation failures; refresh success, genuine revoked-token failure (redirects to `/login`, never loops to `/auth/refresh`), and concurrent-refresh race recovery; dashboard layout's auth-redirect and business-selection branches. |
| Risks | A misconfigured `SESSION_SECRET` in production must fail loudly, not silently fall back — covered by tests with no fallback path in the code. Concurrent refresh attempts (Strict Mode double-effect, multiple tabs hitting the same process) share one backend call via `singleFlightRefresh` in `lib/auth/refresh-lock.ts` — this is what actually prevents the race, not a cookie re-check (an earlier draft of this logic tried re-reading the cookie after a failure to detect a concurrent winner, but `cookies()` in a Server Action only ever reflects that request's own incoming snapshot and can't observe a sibling request's `Set-Cookie`; caught by cross-provider review before merge, fixed before this row was marked done). Known, undefended gap: a horizontally scaled deployment (multiple instances, no sticky sessions) is not covered. Also fixed pre-merge: login always authenticated against the backend's default tenant — added optional `TENANT_SLUG`, sent only on login. |

## 1b. Bookings list and booking details

| Field | Detail |
|---|---|
| Status | **Done** — `feat/frontend-bookings-read` |
| Branch | `feat/frontend-bookings-read` |
| Goal | Real, read-only owner bookings UI: list with the filters/pagination the API actually supports, and a dedicated booking-detail route. |
| Scope | `/dashboard/bookings` (list) and `/dashboard/bookings/[bookingId]` (detail); status filter (`BookingStatus`) and staff filter (real staff list), offset pagination; staff/service name resolution via the real staff/services list endpoints (small, fetched-once lookup maps — not N+1 per row); loading/empty/error states; enables the "Bookings" nav entry (now "active", was "Coming soon"). Introduces `@tanstack/react-query` (the list's filters/pagination are client-driven) and a single `/api/bookings` Route Handler proxy for the list only — the detail page needed no proxy at all: it has no live filters, so it's a plain Server Component fetching directly via `fetchFromBackend`, exactly like the Overview page. |
| Out of scope | Cancellation, rescheduling (separate branches, 1c/1d), date-range filtering (confirmed again: the backend still has no date filter on `GET .../bookings`), customer name/phone display (confirmed again: still no endpoint resolves `customer_id` — list/detail both show `Customer #<id>` with a visible "Name unavailable" note), audit/notification/calendar-sync panels (still not exposed), Playwright (still nothing destructive enough to justify it — lands with 1c). |
| Backend dependencies | `GET /api/v1/businesses/{id}/bookings`, `GET .../bookings/{id}`, `GET .../staff[/{id}]`, `GET .../services/{id}`. Contract re-verified byte-for-byte unchanged since 1a's audit (`git diff` against the routes/schemas at 1a's merge commit was empty) before writing any code. |
| Acceptance | List and detail both reflect the real, current API contract — no fields shown that the backend doesn't actually return. The bookings proxy Route Handler resolves the business from the session itself (`getCurrentBusinessContext`) and ignores any business id a client might send — there is no path for a client-supplied tenant/business id to reach a backend call. `pnpm build` succeeds; TypeScript strict passes. |
| Tests | Proxy route: unauthorized, expired-token-without-calling-backend, no-single-business, client-supplied business id ignored, filter/pagination forwarding, backend error passthrough. List component: loading, empty, error, name-resolution fallback for a deleted staff/service, "Any available" for no-staff-preference, status filter resets to page 1, Previous/Next pagination. Detail page: rendering with resolved names, 404 → `notFound()`, non-numeric id rejected without querying the backend, no-session redirect. List page: server-side staff/services fetch wired into the client component's props. |
| Risks | None found beyond what 1a already flagged for the contract gaps (still accurate, re-verified). |

## 1c. Booking cancellation UI

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-booking-cancel` |
| Goal | Let an owner (admin role) cancel a booking from the detail page, with explicit confirmation. |
| Scope | Cancel button on the booking-detail page (own route, not a modal-as-primary-UI); native `<dialog>` confirmation (optional reason field, mirrors `BookingCancelRequest`); `POST .../bookings/{id}/cancel` via a CSRF-protected Route Handler; role-aware UI — hide the action entirely when the signed-in user's role (from `/auth/me`) isn't `admin`, rather than showing it and letting the backend 403. |
| Out of scope | Rescheduling (separate task, 1d), admin override create/cancel endpoints (separate decision — those bypass normal flows and need their own authorization review), bulk cancellation. |
| Backend dependencies | `POST /api/v1/businesses/{id}/bookings/{id}/cancel` (role `admin`). No gaps. |
| Acceptance | Cancellation requires explicit confirmation; succeeds and updates the UI without a full reload; backend errors (404/409) surface clearly; the button never renders for a non-admin user. |
| Tests | Confirmation dialog interaction; successful cancel mutation; error handling (e.g. already-cancelled); role-based visibility. |
| Risks | A booking that's already been cancelled by someone else between page load and the confirm click — handle the 409/404 from a stale view explicitly, don't assume the click always succeeds. |

## 1d. Booking reschedule UI

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-booking-reschedule` |
| Goal | Let an admin reschedule a booking to a new slot from the detail page. |
| Scope | A slot picker (likely needs an availability-search call, not just a date/time input — confirm the real availability endpoint contract before designing this, don't assume one exists in the shape needed); `POST .../bookings/{id}/reschedule`; same confirmation-before-destructive-change pattern as cancellation. |
| Out of scope | Customer-initiated reschedule (that's IVR-side, already implemented in the backend — this task is the admin/owner UI only). |
| Backend dependencies | `POST /api/v1/businesses/{id}/bookings/{id}/reschedule` (role `admin`); likely the availability API — verify its exact contract (query params, response shape) fresh, the way 1a verified bookings/auth, rather than assuming. |
| Acceptance | Reschedule requires picking a real available slot, not a free-text date/time; succeeds and updates the UI; conflicts surface clearly. |
| Tests | Slot picker interaction; successful reschedule; conflict/error handling. |
| Risks | This is meaningfully more complex than cancellation (needs a working slot picker, not just a confirm dialog) — don't bundle it into 1c's branch even if it seems small at a glance. |

## 2. Calendar / schedule view

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-calendar-view` |
| Goal | A calendar/agenda view of bookings (day/week), for a faster at-a-glance schedule than the list. |
| Scope | Read-only calendar rendering on top of the bookings list endpoint (1b); date navigation. |
| Out of scope | Drag-to-reschedule, external calendar sync UI (the backend's calendar adapter is an internal sync mechanism, not something the owner configures from this view). |
| Backend dependencies | Same as 1b — `GET .../bookings`. Re-confirm whether a date-range filter has been added to the backend by this point; if not, this view has to paginate/filter client-side within whatever the list endpoint supports, which may need a backend follow-up before this task is practical. |
| Acceptance | Calendar viewreflects real bookings; navigating dates doesn't silently show stale/incomplete data. |
| Tests | Date navigation; rendering bookings on the correct day/time in the business's timezone. |
| Risks | Without a backend date filter, a week view may require fetching unbounded pages — flag this as a likely backend blocker before starting, don't work around it client-side with an unbounded fetch loop. |

## 3. Staff management

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-staff-management` |
| Goal | List, add, edit, and deactivate staff. |
| Scope | `/dashboard/staff` list + create/edit forms; uses `PATCH .../staff/{id}` (confirmed implemented in 1a's audit, despite `docs/product/owner-dashboard.md` still listing it as a gap — re-verify the route file directly). |
| Out of scope | Staff-specific working hours (task 5), transfer-eligibility settings (task 8). |
| Backend dependencies | `GET/POST/PATCH /api/v1/businesses/{id}/staff[/{id}]`. |
| Acceptance | Owner can add a staff member, edit name/phone, and deactivate one, without a page reload. |
| Tests | Create/edit form validation; deactivate confirmation; list refresh after mutation. |
| Risks | None beyond standard CRUD form risk. |

## 4. Services management

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-services-management` |
| Goal | List, add, edit, and delete services. |
| Scope | `/dashboard/services` list + create/edit forms + delete confirmation. |
| Out of scope | Multi-service/line-item booking UI (no booking-creation UI exists yet at all). |
| Backend dependencies | `GET/POST/PATCH/DELETE /api/v1/businesses/{id}/services[/{id}]`. |
| Acceptance | Owner can manage the service list the IVR offers, including duration and optional price. |
| Tests | Create/edit/delete forms; validation (duration bounds, price). |
| Risks | Deleting a service that has existing bookings — confirm the backend's actual behavior (block vs. cascade vs. orphan) before designing the delete confirmation copy; don't assume. |

## 5. Working hours and exceptions

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-availability-management` |
| Goal | Configure salon/staff working hours, one-off exceptions, and recurring staff blocks. |
| Scope | `/dashboard/availability`: working-hours CRUD (business-wide and per-staff), availability-exception CRUD, recurring-staff-block CRUD (P3-005). |
| Out of scope | The availability *calculation* itself (already correct server-side per P3-001–P3-005) — this task is purely the configuration UI. |
| Backend dependencies | Working hours, availability-exceptions, and recurring-staff-blocks CRUD endpoints (all exist per the P3 backlog). |
| Acceptance | Owner can fully configure a real schedule without operator help, matching the precedence rules already enforced server-side (salon vs. staff, exceptions, recurring blocks). |
| Tests | CRUD forms for all three resource types; overlap/conflict error display (the backend validates this — surface its errors, don't reimplement the validation client-side). |
| Risks | This is the most config-dense task so far — resist building a generic "schema-driven form" abstraction for three different resource shapes; three similar forms are fine. |

## 6. Clients and booking history

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-clients-crm` |
| Goal | CRM client list and per-client booking history. |
| Scope | `/dashboard/clients` list + detail with booking history (`GET .../clients/{id}/bookings`). |
| Out of scope | GDPR delete UI (sensitive action — needs its own explicit task and authorization review, don't fold it in here). |
| Backend dependencies | `GET/POST/PATCH /api/v1/businesses/{id}/clients[/{id}]`, `GET .../clients/{id}/bookings`. |
| Acceptance | Owner can browse clients and see a given client's past bookings. |
| Tests | List/detail rendering; booking-history pagination. |
| Risks | A `Client` is optionally linked to a `Customer` (`customer_id` nullable) — don't assume every client has one; the booking-list gap (1b's "no customer lookup") doesn't apply here since this task starts from the `Client` resource, which does carry its own name/phone. |

## 7. Waitlist management

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-waitlist-management` |
| Goal | View and manage waitlist entries. |
| Scope | `/dashboard/waitlist` list, status (WAITING/OFFERED/CONFIRMED/EXPIRED/CANCELLED) display. |
| Out of scope | Manually triggering an offer (the backend's offer/escalation flow is automatic on cancellation/timeout — verify whether a manual trigger endpoint exists before assuming this is just a read view). |
| Backend dependencies | Verify the actual waitlist read endpoint(s) exist before starting — not confirmed during 1a's audit (out of this branch's scope). |
| Acceptance | TBD pending backend endpoint verification. |
| Tests | TBD. |
| Risks | Don't assume a list endpoint exists just because the model does — re-run the same kind of route-file audit 1a did for bookings/auth. |

## 8. IVR and transfer settings

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-ivr-settings` |
| Goal | Configure call transfer settings (business-level enable/policy, staff eligibility). |
| Scope | `/dashboard/voice`: transfer settings form, staff transfer-eligibility toggles. |
| Out of scope | IVR prompt content/localization (P3-009's prompt-key architecture is a backend/ops concern, not owner-configurable here), live call monitoring. |
| Backend dependencies | Business transfer settings fields (part of `BusinessUpdate`), staff transfer-eligibility fields — verify exact field names on `Staff`/`Business` schemas before starting. |
| Acceptance | Owner can configure transfer without operator help. |
| Tests | Settings form validation and persistence. |
| Risks | None identified yet — needs its own backend contract check first. |

## 9. Notifications / integration status

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-integration-status` |
| Goal | Surface SMS/calendar integration health (sent/failed counts, DLQ depth) to the owner. |
| Scope | TBD — **no notification/calendar-sync read endpoint exists yet** (confirmed during 1a's audit; the only signals are Prometheus metrics and a DLQ depth gauge, not an owner-facing API). |
| Out of scope | Everything, until a backend endpoint exists. |
| Backend dependencies | **Blocked.** Needs a new backend read endpoint before this task is practical — not just a frontend gap. |
| Acceptance | N/A until backend work lands. |
| Tests | N/A. |
| Risks | Don't build this against the Prometheus/metrics surface directly from the browser — that's an operator-facing system, not a tenant-scoped API; wait for a real backend endpoint. |

## 10. Onboarding wizard

| Field | Detail |
|---|---|
| Status | Not started |
| Branch | `feat/frontend-onboarding-wizard` |
| Goal | Guided setup UI on top of the existing `POST /api/v1/onboarding` endpoint (AVS-L004/P4-005). |
| Scope | Multi-step form: business profile, staff, services, working hours, submitted as one atomic call. |
| Out of scope | Self-service tenant/account signup (P4-004's other half — creating a new tenant/admin user — is still backend work, not implemented; this task is just the guided setup *after* an account exists). |
| Backend dependencies | `POST /api/v1/onboarding` (exists, atomic). |
| Acceptance | A brand-new business can be fully configured through one guided flow. |
| Tests | Multi-step form state, validation per step, final submission. |
| Risks | None identified — the backend endpoint is already atomic, so partial-failure handling is simpler than it would otherwise be. |

## 11. Owner metrics dashboard

| Field | Detail |
|---|---|
| Status | **Blocked on backend P2-013** |
| Branch | `feat/frontend-owner-metrics` |
| Goal | Real booking/conversion/failure metrics on the dashboard overview. |
| Scope | TBD — depends entirely on what P2-013's eventual response shape looks like. |
| Out of scope | Anything resembling the fake-chart/invented-number patterns explicitly ruled out for this whole epic — that restriction doesn't lift just because a metrics endpoint eventually exists; only show what it actually returns. |
| Backend dependencies | **`docs/appointment-saas-roadmap.md` P2-013 (owner metrics API) — not implemented.** Do not start this task before it ships. |
| Acceptance | N/A until backend work lands. |
| Tests | N/A. |
| Risks | N/A. |

## 12. CSV export

| Field | Detail |
|---|---|
| Status | **Blocked on backend P2-014** |
| Branch | `feat/frontend-csv-export` |
| Goal | Export bookings/customers within the tenant. |
| Scope | TBD — depends on P2-014's endpoint contract. |
| Out of scope | Client-side CSV generation from paginated list data (the roadmap's P2-014 acceptance criteria require tenant-scoped, *bounded* exports — that's a backend job, not something to fake by walking pagination in the browser). |
| Backend dependencies | **`docs/appointment-saas-roadmap.md` P2-014 (CSV export) — not implemented.** Do not start this task before it ships. |
| Acceptance | N/A until backend work lands. |
| Tests | N/A. |
| Risks | N/A. |

## 13. Billing UI

| Field | Detail |
|---|---|
| Status | **Blocked on backend P4-007 through P4-010** |
| Branch | `feat/frontend-billing` |
| Goal | Subscription/plan management UI. |
| Scope | TBD — entirely dependent on the eventual Stripe Billing model, plan/limits design, and webhook-driven state. |
| Out of scope | Anything billing-related before the backend model exists — there is currently no Stripe integration, no plan-limit enforcement, and no billing webhook handling in this codebase at all. |
| Backend dependencies | **`docs/appointment-saas-roadmap.md` P4-007–P4-010 — none implemented.** `PlanPolicyService` is an intentional stub today; do not build a UI against a stub. |
| Acceptance | N/A until backend work lands. |
| Tests | N/A. |
| Risks | N/A. |
