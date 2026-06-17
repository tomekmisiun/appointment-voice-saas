# Owner Dashboard — MVP Scope (AVS-L003)

Defines what pages and API routes are needed for a minimal owner-facing UI.
This document is the agreed scope — no frontend exists yet. Build against it
when the frontend work starts (or hand to an external frontend team).

---

## Design constraints

- Backend is API-first. The dashboard is a separate frontend (SPA, mobile app,
  or even a no-code tool) that calls the existing REST API.
- The owner authenticates via JWT (existing `/api/v1/auth` routes).
- An owner user belongs to one tenant. They see only their own businesses.
- No admin-level access: owners cannot create tenants, manage other tenants'
  users, or read leads for other owners.
- Out of scope for this skeleton: Stripe billing, phone provisioning, analytics
  beyond basic booking counts, calendar UI.

---

## Auth flow

The owner logs in the same way any user does:

```
POST /api/v1/auth/login
{ "username": "<email>", "password": "<password>" }
→ { "access_token": "...", "token_type": "bearer" }
```

The token is used as `Authorization: Bearer <token>` on all subsequent requests.

Password reset is handled via existing `/api/v1/auth/...` routes.

---

## Pages and required API routes

### 1. Dashboard home — booking overview

**Goal:** Quick snapshot of today's bookings and recent activity.

| Need | Endpoint | Notes |
|------|----------|-------|
| List today's bookings | `GET /api/v1/businesses/{id}/bookings?date_from=<today>&date_to=<today>` | Filter by date range |
| Count confirmed / cancelled | Same endpoint, client-side aggregate | |
| Business name / mode | `GET /api/v1/businesses/{id}` | |

**Proposed new endpoints needed:** None — existing bookings list is sufficient
for MVP. A `/api/v1/businesses/{id}/bookings/summary` convenience endpoint
would improve performance for a production dashboard but is not required now.

---

### 2. Bookings list

**Goal:** Owner can see all bookings, filter, and cancel.

| Need | Endpoint | Notes |
|------|----------|-------|
| List bookings (paginated) | `GET /api/v1/businesses/{id}/bookings?page=&size=` | Existing |
| Cancel a booking | `DELETE /api/v1/businesses/{id}/bookings/{booking_id}` | Existing (returns 200 with `status: cancelled`) |
| View single booking | `GET /api/v1/businesses/{id}/bookings/{booking_id}` | Needs to be added — currently only list exists |

**Gap: `GET /api/v1/businesses/{id}/bookings/{booking_id}`** does not exist.
Required before the bookings detail page can be built. See AVS-L003-GAP-001.

---

### 3. Business settings

**Goal:** Owner can update their business name, phone, booking mode, and
external booking URL without calling the operator.

| Need | Endpoint | Notes |
|------|----------|-------|
| Read settings | `GET /api/v1/businesses/{id}` | Existing |
| Update name / phone / timezone | `PATCH /api/v1/businesses/{id}` | Existing |
| Switch booking mode | `PATCH /api/v1/businesses/{id}` with `booking_mode` | Existing (with validators) |
| Update external URL | `PATCH /api/v1/businesses/{id}` with `external_booking_url` | Existing |

No new endpoints needed for this page.

---

### 4. Staff management

**Goal:** Owner can add, edit, and deactivate staff members.

| Need | Endpoint | Notes |
|------|----------|-------|
| List staff | `GET /api/v1/businesses/{id}/staff` | Existing |
| Add staff | `POST /api/v1/businesses/{id}/staff` | Existing |
| Update staff (name, phone, active) | `PATCH /api/v1/businesses/{id}/staff/{staff_id}` | Needs to be added — see AVS-L003-GAP-002 |
| Deactivate staff | `PATCH` with `is_active: false` | Same gap as above |

**Gap: `PATCH /api/v1/businesses/{id}/staff/{staff_id}`** does not exist.
Required before staff edit/deactivate flow can be built. See AVS-L003-GAP-002.

---

### 5. Services management

**Goal:** Owner can manage the list of services the IVR offers.

| Need | Endpoint | Notes |
|------|----------|-------|
| List services | `GET /api/v1/businesses/{id}/services` | Existing |
| Add service | `POST /api/v1/businesses/{id}/services` | Existing |
| Update service | `PATCH /api/v1/businesses/{id}/services/{service_id}` | Needs to be added — see AVS-L003-GAP-003 |
| Delete service | `DELETE /api/v1/businesses/{id}/services/{service_id}` | Needs to be added — see AVS-L003-GAP-003 |

**Gap: service update/delete endpoints** do not exist. See AVS-L003-GAP-003.

---

### 6. Working hours

**Goal:** Owner can configure when the IVR offers booking slots.

| Need | Endpoint | Notes |
|------|----------|-------|
| View hours | `GET /api/v1/businesses/{id}/working-hours` | Existing |
| Set hours for a day | `POST /api/v1/businesses/{id}/working-hours` | Existing |
| Update a schedule row | `PATCH /api/v1/businesses/{id}/working-hours/{id}` | Needs to be added — see AVS-L003-GAP-004 |
| Delete a schedule row | `DELETE /api/v1/businesses/{id}/working-hours/{id}` | Needs to be added — see AVS-L003-GAP-004 |

**Gap: working hours update/delete endpoints** do not exist. See AVS-L003-GAP-004.

---

### 7. Availability exceptions (closures / special hours)

**Goal:** Owner can block out holidays and add one-off special hours.

| Need | Endpoint | Notes |
|------|----------|-------|
| List exceptions | `GET /api/v1/businesses/{id}/availability-exceptions` | Existing |
| Add exception | `POST /api/v1/businesses/{id}/availability-exceptions` | Existing |
| Delete exception | `DELETE /api/v1/businesses/{id}/availability-exceptions/{id}` | Needs to be added — see AVS-L003-GAP-005 |

**Gap: exception delete endpoint** does not exist. See AVS-L003-GAP-005.

---

## API gaps summary (AVS-L003 backlog)

These are the endpoints needed to unlock the dashboard but not yet built.
Implement them when AVS-L003 frontend work begins.

| ID | Gap | Route | Priority |
|----|-----|-------|----------|
| AVS-L003-GAP-001 | Single booking read | `GET /businesses/{id}/bookings/{booking_id}` | P2 |
| AVS-L003-GAP-002 | Staff update / deactivate | `PATCH /businesses/{id}/staff/{staff_id}` | P2 |
| AVS-L003-GAP-003 | Service update / delete | `PATCH /businesses/{id}/services/{service_id}`, `DELETE ...` | P2 |
| AVS-L003-GAP-004 | Working hours update / delete | `PATCH /businesses/{id}/working-hours/{id}`, `DELETE ...` | P2 |
| AVS-L003-GAP-005 | Availability exception delete | `DELETE /businesses/{id}/availability-exceptions/{id}` | P2 |

All gaps are CRUD completions on existing resources — no new models or
migrations are required.

---

## Auth and tenancy requirements for owner-facing routes

Existing business routes use `Depends(get_current_business(business_id))` or
equivalent which already validates that the business belongs to the
authenticated user's tenant. Owner users must not be able to read or modify
businesses belonging to another tenant.

When adding the gap endpoints above, apply the same `require_business()` /
`get_current_business()` pattern already used in the codebase. Do not bypass
tenant isolation.

---

## Not in scope for AVS-L003

- Frontend implementation (HTML/CSS/JS/React — separate project)
- Booking analytics beyond count (charts, revenue, trends)
- Stripe billing or subscription management (P4-007–P4-010)
- Phone provisioning UI (P4-006)
- Customer / CRM view (P2-001–P2-003)
- Notifications settings (email preferences, SMS opt-out)
- Multi-business owner support (owner managing >1 business)

---

## Later upgrade path

```
AVS-L003  ← agreed dashboard scope (this document)
    │
AVS-L004  ← self-service onboarding API (P4)
    │
P2-001    ← CRM clients table
P4-005    ← guided onboarding wizard
P4-007+   ← Stripe Billing
```
