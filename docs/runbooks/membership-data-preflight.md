# Membership Data Preflight Runbook (SAC-001)

Read-only audit that produces deterministic counts and ambiguity reports on
the current `Tenant` / `Business` / `User` / `Staff` data, so the membership
schema (SAC-003) and backfill (SAC-004) can be designed from evidence. See
`docs/product/staff-access-calendar-roadmap.md` and
`docs/adr/0007-separate-staff-records-from-login-identities.md`.

The script (`app/ops/membership_preflight.py`) performs no schema or data
mutation: no `INSERT`/`UPDATE`/`DELETE`/DDL.

## Running it

Local/dev:

```
docker compose run --rm api python -m app.ops.membership_preflight
```

Production:

```
docker compose -f docker-compose.prod.yml run --rm api \
  python -m app.ops.membership_preflight
```

## Handling the output

- Emails and phone numbers in the report are masked (first character +
  domain for emails, last two digits for phones). Tenant/user/staff IDs and
  counts are not sensitive and are shown in full.
- Do not redirect the output into a file committed to git. If you need to
  archive a run, save it outside the repository (e.g. an internal ticket or
  a secrets-handling-approved location).
- The report distinguishes **safe** tenants (exactly one business, exactly
  one admin/platform_admin user, no email shared with another tenant) from
  tenants requiring manual resolution before SAC-004 backfill, with one or
  more reasons:
  - `no_business` / `multiple_businesses`
  - `no_admin` / `multiple_admins`
  - `duplicate_email_across_tenants`
- `-- Signup ownership evidence --` lists, per tenant with a
  `tenant.created` audit log entry, the recorded `source` (e.g.
  `self_signup`) and how many admin-role users that tenant has. A
  `self_signup` tenant with exactly one admin user is the strongest evidence
  of who owns that tenant; anything else needs a manual decision in the
  SAC-002 migration runbook.
- `-- Orphan/mismatched staff references --` lists `Staff` rows whose
  `tenant_id` does not match the `tenant_id` of their referenced `Business`.
  The application (`require_business()` in `app/services/staff_service.py`)
  prevents creating new rows like this; any rows found here predate that
  check or came from a manual data fix and need a one-off correction before
  SAC-003.

## Definition of done for this run

- Record the date of the run and a link to where the masked output was
  archived in the SAC-002 migration runbook.
- Every tenant flagged for manual resolution has a documented decision (or
  an open follow-up) before SAC-004 backfill starts.
