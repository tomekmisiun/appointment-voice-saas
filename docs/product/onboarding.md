# Pilot Onboarding Runbook (AVS-L002)

Step-by-step guide for an operator to onboard a salon from a submitted
`OwnerLead` to a live IVR pilot. Work through each section in order.
Two paths diverge at Step 4 based on `booking_mode_interest`.

Prerequisites: the platform is deployed per
[`../operations/deployment.md`](../operations/deployment.md). You have an
admin JWT.

---

## Step 1 — Review the lead

```
GET /api/v1/owner-leads?status=new
Authorization: Bearer <admin_token>
```

Find the lead for this salon. Note:
- `id` — lead ID (used throughout this runbook)
- `business_name`
- `booking_mode_interest` — `external_booking_link` or `standalone_booking`
- `external_booking_url` — Booksy / other URL (external mode only)

If lead details look incomplete, contact the owner before proceeding.

```
PATCH /api/v1/owner-leads/{lead_id}/status
{ "status": "contacted" }
```

---

## Step 2 — Qualify the lead

During the owner call, confirm:

**For `external_booking_link`:**
- [ ] Owner has an active Booksy (or other) profile URL ready.
- [ ] Owner's missed-call phone number is known (the Twilio number will ring it).
- [ ] Owner confirms they want callers to receive an SMS with the booking URL.

**For `standalone_booking`:**
- [ ] Owner can supply: list of services (name + duration + price), staff names and phones, weekly schedule.
- [ ] Owner does not already use an external booking platform that would conflict.

After qualifying:

```
PATCH /api/v1/owner-leads/{lead_id}/status
{ "status": "qualified" }
```

---

## Step 3 — Create the tenant and admin user

> Skip if onboarding into an existing tenant (e.g. a multi-business operator).

```
POST /api/v1/admin/tenants
Authorization: Bearer <admin_token>
{ "name": "<salon_slug>", "display_name": "<Salon Name>" }
```

Save the `tenant_id` returned. Then create an owner user (optional — needed
only if the owner will later access the admin dashboard):

```
POST /api/v1/auth/register
{
  "email": "<owner_email>",
  "password": "<temp_password>",
  "tenant_id": "<tenant_id>"
}
```

Instruct the owner to change the password on first login.

---

## Step 4A — External booking link mode

Use when `booking_mode_interest == external_booking_link`.

### 4A-1. Create the business

```
POST /api/v1/businesses
Authorization: Bearer <admin_token>
{
  "tenant_id": "<tenant_id>",
  "name": "<Salon Name>",
  "phone": "<owner_phone>",
  "timezone": "Europe/Warsaw",
  "booking_mode": "external_booking_link",
  "external_booking_url": "<https://booksy.com/...>",
  "external_booking_label": "Book at <Salon Name>",
  "external_booking_provider": "booksy"
}
```

Save the `business_id`.

### 4A-2. Configure call transfer (optional)

If the owner also wants press-2-to-transfer:

```
PATCH /api/v1/businesses/{business_id}
{
  "transfer_enabled": true,
  "transfer_policy": "business_phone",
  "transfer_phone": "<salon_phone>"
}
```

### 4A-3. Skip to Step 5

No staff, services, or working hours configuration is required for external
booking link mode. IVR press-1 sends the SMS link; no booking row is created.

---

## Step 4B — Standalone booking mode

Use when `booking_mode_interest == standalone_booking`.

### 4B-1. Create the business

```
POST /api/v1/businesses
Authorization: Bearer <admin_token>
{
  "tenant_id": "<tenant_id>",
  "name": "<Salon Name>",
  "phone": "<salon_phone>",
  "timezone": "Europe/Warsaw",
  "booking_mode": "internal_booking"
}
```

Save the `business_id`.

### 4B-2. Add staff members

For each staff member:

```
POST /api/v1/businesses/{business_id}/staff
{
  "name": "<Staff Name>",
  "phone": "<+48XXXXXXXXX>",
  "is_active": true
}
```

If no individual staff is relevant (solo operator), create one staff entry for
the owner. The phone must be set if transfer-to-staff is desired.

### 4B-3. Add services

For each service offered:

```
POST /api/v1/businesses/{business_id}/services
{
  "name": "<Service Name>",
  "duration_minutes": <30|45|60>,
  "price": <price_in_pln_as_decimal>
}
```

Up to 9 services are exposed in the IVR keypad.

### 4B-4. Set working hours

For each weekday the salon is open:

```
POST /api/v1/businesses/{business_id}/working-hours
{
  "day_of_week": <0=Mon … 6=Sun>,
  "start_time": "09:00",
  "end_time": "17:00",
  "staff_id": null
}
```

Set `staff_id` to override hours per-staff if needed.

### 4B-5. Configure call transfer (optional)

```
PATCH /api/v1/businesses/{business_id}
{
  "transfer_enabled": true,
  "transfer_policy": "staff",
  "transfer_phone": null
}
```

With `transfer_policy: "staff"`, IVR press-2 resolves to a random active
staff member with a non-null phone. Use `transfer_policy: "business_phone"`
and set `transfer_phone` to route to a single number.

---

## Step 5 — Verify IVR via simulation

Run a simulated call to confirm the IVR behaves as expected.

### Incoming call

```
POST /api/v1/ivr/simulate/call
{ "business_id": "<business_id>", "caller_phone": "+48000000000" }
```

Expected:
- `action: CONTINUE`
- `session_id` returned

### Press 1

```
POST /api/v1/ivr/simulate/press
{ "session_id": "<session_id>", "key": "1" }
```

**External mode**: expect `action: CONTINUE`, `step: EXTERNAL_LINK_SENT`.
No further interaction needed.

**Standalone mode**: expect service selection prompt. Continue:

```
POST /api/v1/ivr/simulate/press   { "session_id": "...", "key": "1" }  # select service 1
```

If the business has 2+ active staff, the next prompt is staff selection
(every staff member is offered, even ones with no individual schedule —
they follow the salon's hours per P3-002):

```
POST /api/v1/ivr/simulate/press   { "session_id": "...", "key": "0" }  # any available staff
POST /api/v1/ivr/simulate/press   { "session_id": "...", "key": "1" }  # select slot 1
```

With 0 or 1 active staff, that step is skipped automatically — go straight
to selecting a slot instead.

Expect `action: CONTINUE`, `step: BOOKING_CONFIRMED`. Verify:

```
GET /api/v1/businesses/{business_id}/bookings
```

A booking with `status: confirmed` should appear.

### Press 2 (transfer — if enabled)

```
POST /api/v1/ivr/simulate/call
{ "business_id": "<business_id>", "caller_phone": "+48000000001" }

POST /api/v1/ivr/simulate/press
{ "session_id": "...", "key": "2" }
```

Expected: `action: TRANSFER`, `transfer_destination: <configured_phone>`.

If `action: CONTINUE` with `step: TRANSFER_UNAVAILABLE` — check transfer
settings and that at least one staff member has a non-null phone.

---

## Step 6 — Check notification outbox

After a standalone booking, confirm the SMS intents were queued:

```
# (query DB directly or via future admin endpoint)
SELECT * FROM notification_outbox
WHERE business_id = '<business_id>'
ORDER BY created_at DESC
LIMIT 5;
```

With `SMS_PROVIDER=twilio` (production), `status` should transition
`PENDING → SENT`. With `SMS_PROVIDER=fake`, check worker logs.

---

## Step 7 — Record the business ID against the lead and mark onboarded

Update lead status:

```
PATCH /api/v1/owner-leads/{lead_id}/status
{ "status": "onboarded" }
```

Note the mapping `lead_id → business_id` in the pilot CRM sheet (or wherever
pilot accounts are tracked) until an owner dashboard is available (AVS-L003).

---

## Step 8 — Hand off to the owner

Tell the owner:

- The Twilio phone number that callers should dial (provisioned separately —
  see `docs/integrations/twilio.md`).
- **External mode**: callers will receive an SMS with their Booksy URL when they
  press 1.
- **Standalone mode**: callers can book directly in the IVR. Confirmations are
  sent by SMS. If Google Calendar is enabled, events are synced automatically.
- They can contact you to update services, hours, or staff.

---

## Rejecting a lead

If the salon is not a fit:

```
PATCH /api/v1/owner-leads/{lead_id}/status
{ "status": "rejected" }
```

No business or tenant is created. The lead record is retained for reference.

---

## Quick-reference: lead status lifecycle

```
new → contacted → qualified → onboarded
                            → rejected
```

All transitions are reversible via the same PATCH endpoint.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| IVR press-1 returns `EXTERNAL_LINK_SENT` but caller gets no SMS | Worker not running or SMS_PROVIDER=fake | Start worker; check `notification_outbox.status` |
| IVR press-2 returns `TRANSFER_UNAVAILABLE` | No active staff with phone, or transfer_enabled=false | Check business transfer settings; ensure staff have phones |
| No slots available for standalone booking | No working hours configured, or all slots taken | Add/check working hours; check existing bookings |
| `POST /api/v1/ivr/simulate/call` returns 404 | Wrong `business_id` or business not in tenant | Verify `business_id` and that business `is_active=true` |
| Migration error on deploy | Stale migration head | Run `alembic upgrade head`; check `alembic heads` for multiple heads |
