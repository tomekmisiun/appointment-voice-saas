# Owner Acquisition and Manual Pilot Onboarding

## Overview

For the first pilot, we do **not** build a full self-service owner dashboard.
The goal is a simple, manually-operated path:

1. A salon owner sees an offer (landing page, direct link, word of mouth).
2. They submit interest via the public lead intake form.
3. We store the lead in the backend.
4. The platform operator reviews the lead and onboards the salon manually.
5. Later this evolves into owner dashboard / onboarding wizard / billing.

---

## First Pilot Owner Flow

```
Owner interest
      │
      ▼
POST /api/v1/owner-leads   ← public endpoint, no auth, rate-limited
      │
      ▼
OwnerLead stored (status = new)
      │
      ▼
Operator reviews via GET /api/v1/owner-leads (admin auth required)
      │
      ├─ PATCH /api/v1/owner-leads/{id}/status → contacted
      │
      ├─ Manual phone call / email with owner
      │
      ├─ PATCH → qualified
      │
      ├─ Operator runs manual onboarding (see AVS-L002 runbook)
      │
      └─ PATCH → onboarded
```

---

## Booking Modes

Two operational modes for the onboarded salon:

### External booking link (Booksy / other platform)

The salon already uses an external booking platform (e.g. Booksy).  
The IVR catches missed calls and sends the caller an SMS with the external booking URL.

- No Booking rows created in our database.
- No internal availability/service configuration required.
- The owner provides their Booksy (or other) profile URL in the lead form.
- On onboarding: set `booking_mode = external_booking_link` and `external_booking_url`.

### Standalone booking (full internal IVR)

The salon does not use an external booking platform.  
The IVR provides full service/slot selection and creates a booking in our database.

- Requires: staff, services, and working hours configured.
- Booking confirmation SMS sent to customer and business.
- Calendar sync available via adapter.
- On onboarding: set `booking_mode = internal_booking`, configure staff/services/hours.

### Not sure

Use when the owner is interested but hasn't decided their setup yet.  
Do not set `external_booking_url` required in this case.

---

## Lead Intake API

### Submit a lead (public)

```
POST /api/v1/owner-leads
Content-Type: application/json

{
  "business_name": "Salon XYZ",
  "owner_name": "Anna",
  "email": "anna@example.com",
  "phone_number": "+48123123123",
  "city": "Gdańsk",
  "booking_mode_interest": "external_booking_link",
  "external_booking_url": "https://booksy.com/...",
  "message": "Chcę przetestować IVR po godzinach."
}
```

- **No authentication required.**
- Rate-limited: 5 submissions per IP per hour.
- `email` and `phone_number` are required.
- `external_booking_url` is required when `booking_mode_interest = external_booking_link`.
- URL must start with `http://` or `https://`.
- Response returns only public-safe fields (no phone, email, message exposed).

### View leads (admin)

```
GET /api/v1/owner-leads                  # list all, paginated
GET /api/v1/owner-leads?status=new       # filter by status
GET /api/v1/owner-leads/{id}             # single lead, full fields
PATCH /api/v1/owner-leads/{id}/status   # update status
```

All admin endpoints require `Authorization: Bearer <access_token>` with admin role.

### Lead statuses

| Status | Meaning |
|--------|---------|
| `new` | Submitted, not yet reviewed |
| `contacted` | We reached out to the owner |
| `qualified` | Owner confirmed interest, ready for onboarding |
| `onboarded` | Salon is live in the system |
| `rejected` | Not a fit for the pilot |

---

## Phone Handling

- Phone numbers are stored as-submitted (`phone_number`) and normalized (`phone_normalized`).
- Normalization strips spaces, dashes, and other separators, keeping only digits and `+`.
- Phone numbers are **not logged** to avoid PII leakage.

---

## Data Model Notes

`OwnerLead` is intentionally **not tenant-scoped**.  
Leads represent people who do not yet have a tenant in the system.  
The platform operator (admin of the default tenant) can read and manage all leads.

---

## Intentionally Out of Scope

- Full owner self-service dashboard (see AVS-L003 for future skeleton)
- Billing or subscription setup (see P4-007 through P4-010)
- Phone number provisioning (see P4-006)
- Automated onboarding wizard (see AVS-L004, P4-005)
- Email/SMS to the owner after lead submission
- Duplicate detection across leads (same email / phone)

---

## Later Upgrade Path

```
AVS-L001  ← manual pilot intake (done)
    │
AVS-L002  ← operator runbook for manual onboarding
    │
AVS-L003  ← minimal owner dashboard skeleton (P2)
    │
AVS-L004  ← self-service onboarding API (P4)
    │
P4-005    ← guided onboarding wizard
P4-007+   ← Stripe Billing / plan limits
```
