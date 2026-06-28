> [!WARNING]
> This document is archived and does not describe the current state of the project.
> See the current documentation: [`../../README.md`](../../README.md) and [`../../../README.md`](../../../README.md).

# Documentation Audit — 2026-06-27

Branch: `chore/docs-audit-and-reset`

## 1. Project State Summary (from code, not docs)

**Repository:** VoxSlot / appointment-voice-saas  
**Backend:** FastAPI, Python 3.13, SQLAlchemy 2.0, Alembic (43 migrations, single head `demo_user_flag_a1b2c3d4`)  
**Frontend:** Next.js 16, TypeScript, pnpm, Tailwind CSS v4 (Node.js ≥22.13.0, pnpm 11.8.0)  
**Infrastructure:** Railway (3 services: api, worker, frontend); PostgreSQL 17, Redis 7, MinIO/S3

### What is implemented (verified from code)

- Multi-tenant FastAPI backend with JWT auth, RBAC, audit logs, rate limiting
- Core booking domain: Business, Staff, Service, WorkingHours, RecurringStaffBlock, AvailabilityException
- Booking engine with DB-level double-booking prevention (btree_gist EXCLUDE)
- Availability engine (salon/staff hours intersection, DST, exceptions, recurring blocks)
- Notification outbox, Twilio SMS + fake providers, reminder/cancellation/waitlist SMS
- Calendar adapter (fake provider + outbox-backed sync, ADRs 0005/0006 scope future)
- IVR full flow via Twilio webhooks + local simulator (`/api/v1/ivr/simulate/call`, `/press`)
- Call transfer (business_phone and staff policies, unavailable fallback)
- SMS reply handling (confirm/cancel)
- IVR reschedule flow (option 3 on main menu)
- CRM clients, booking history, GDPR anonymize
- Waitlist (offer on cancellation, timeout escalation, row-locking)
- Multi-service bookings (BookingLineItem model; not yet wired into IVR)
- Pending payment hold (PENDING_PAYMENT status, hold expiry, refund endpoint)
- Multilingual IVR prompt architecture (P3-009, EN only, PL via data change)
- Recurring staff blocks (P3-005)
- Admin override, reconciliation job (P3-012/013)
- Self-service signup (`POST /api/v1/signup`), onboarding wizard
- Owner lead intake (`POST /api/v1/owner-leads`)
- Demo mode (read-only, seeded data, `/demo` route)
- BusinessMembership model (sac003 migration done); RBAC from membership **not yet wired** (SAC-005)
- Next.js dashboard: landing page, login, registration, demo, bookings list/detail, staff list, cancel/reschedule dialogs

### What is NOT implemented on `main`

- BusinessPhoneNumber model, telephony_status column (on backup snapshot branch only)
- Phone-number-based IVR routing (current: URL-embedded business_id)
- SMS localization / per-business language (EN only, hardcoded)
- Public booking management link (HMAC token, public cancel/reschedule)
- SAC-005 RBAC cutover (membership.role not used in auth decisions)
- SAC-006/007/008b/009 (staff lifecycle, service assignments, invitations — on snapshot branch)
- Owner metrics API (P2-013), CSV export (P2-014)
- Frontend configuration screens (services, hours, blocks, exceptions, IVR simulator UI)
- Stripe payment links (P3-007, deliberately deferred)
- Billing/subscriptions (P4-007 through P4-010)
- `docs/learning/00-current-state-audit.md` (referenced by .ai-rules/documentation.md; directory missing)

### Production status (2026-06-27)

- Frontend (`voxslot.up.railway.app`): HTTP 200 — LIVE
- API (`api-production-52a1.up.railway.app`): **502 Bad Gateway — DOWN**
- Worker: unknown (depends on API)

---

## 2. Documentation Decision Table

| File | Role | Problem | Decision | Justification |
|------|------|---------|----------|---------------|
| `.ai-rules/**` (17 files) | Binding AI rules | — | **NEVER TOUCH** | Source of truth for all agent behavior |
| `AGENTS.md` | Agent entry point | — | **NEVER TOUCH** | Binding workflow file |
| `CLAUDE.md` | Claude Code config | — | **NEVER TOUCH** | Binding workflow file |
| `.claude/agents/code-reviewer.md` | Code reviewer agent | — | **NEVER TOUCH** | Binding agent definition |
| `.commands/**` (9 files) | Agent prompt formats | — | **NEVER TOUCH** | Optional but referenced by workflows |
| `agents/**` (6 files) | Review personas | — | **NEVER TOUCH** | Optional reviewer personas |
| `docs/development/workflows/ai-workflows.md` | AI workflow index | — | **NEVER TOUCH** | Workflow reference |
| `docs/development/workflows/two-agent-review.md` | Review workflow | — | **NEVER TOUCH** | Workflow reference |
| `docs/adr/**` (8 ADRs + README) | Architecture decisions | — | **KEEP — annotate only** | Historical decision records; ADR 0008 supersedes parts of 0005/0006 (noted in adr/README.md) |
| `.github/DEPLOY.md` | Railway deployment doc | — | **KEEP** | Recently updated; authoritative for production deploy |
| `README.md` | Project landing page | Node.js requirement says "20+" (should be 22+); Roadmap section has stale items | **UPDATE** | Fix Node version; update roadmap bullet list |
| `PROJECT_STATUS.md` | Verified capabilities | Stale at 2026-06-22; missing P3-013/008/010/014, P4-004, telephony status | **UPDATE** | Add pointer to docs/project/current-state.md; add note about post-June-22 completions |
| `ROADMAP.md` | High-level roadmap | — | **KEEP** | Updated 2026-06-27 in same PR |
| `TECH_DEBT.md` | Tech debt register | — | **KEEP** | Updated 2026-06-27 in same PR |
| `docs/archive/legacy/template-freeze-checklist-root.md` | Template pointer | — | **KEEP** | Referenced by .ai-rules/context-map.md; valid pointer |
| `docs/project/current-state.md` | Full audit snapshot | — | **KEEP** | New, accurate (2026-06-27) |
| `docs/project/implementation-backlog.md` | Executable backlog | — | **KEEP** | Referenced by .ai-rules; authoritative backlog |
| `docs/audits/AUDIT_CURRENT_REPO_STATE.md` | 2026-06-27 audit | — | **KEEP** | New, accurate |
| `docs/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md` | Recovery audit | — | **KEEP** | Recent, accurate |
| `docs/audits/p3-remaining-backlog-audit.md` | P3 audit | Historical | **KEEP** | Historical reference (2026-06-22) |
| `docs/audits/pre-p3-readiness-audit.md` | Security audit | Historical | **KEEP** | Historical reference |
| `docs/audits/staff-access-calendar-current-state.md` | SAC state | Historical | **KEEP** | Historical reference for SAC epic |
| `docs/adr/README.md` | ADR index | Lists only ADR 0001; missing 0002-0008 | **UPDATE** | Add all 8 ADRs and supersession note — Note: wait, the adr/README.md already has all 8! Verified in earlier read. The `docs/archive/superseded/decisions-readme.md` is the stale one. |
| `docs/archive/superseded/decisions-readme.md` | ADR format guide | Table only has ADR 0001; missing 0002-0008; referenced by .ai-rules/context-map.md | **UPDATE** | Add ADRs 0002-0008 to the index table |
| `docs/development/workflows/ai-workflows.md` | Workflow reference | — | **NEVER TOUCH** | Workflow file |
| `docs/operations/backups/overview.md` | Backup automation | — | **KEEP** | Operational runbook; cross-referenced |
| `docs/development/ci-policy.md` | CI policy reference | — | **KEEP** | Referenced by .ai-rules/repository.md |
| `docs/development/commands.md` | Makefile reference | — | **KEEP** | Useful reference; linked from README and template docs |
| `docs/operations/backups/restore.md` | Backup procedures | — | **KEEP** | Operational runbook; cross-referenced |
| `docs/archive/superseded/demo-flow.md` | Local demo flow | Endpoint paths stale: `/incoming` → `/call`, `/input` → `/press`; seed command | **UPDATE** | Fix IVR simulator endpoint names to match app/api/routes/ivr.py |
| `docs/architecture/domain-model.md` | Domain vocabulary | Header says "not implemented unless in PROJECT_STATUS.md" — all models are now implemented | **UPDATE** | Update disclaimer; models are implemented; keep as domain reference |
| `docs/operations/runbooks/file-uploads.md` | Upload ops | — | **KEEP** | Referenced by .ai-rules/context-map.md |
| `docs/archive/legacy/README.md` | Foundation pointer | — | **KEEP** | Historical reference index |
| `docs/archive/legacy/template-*.md` (4 files) | Template history | — | **KEEP** | Historical reference; referenced by docs/archive/legacy/README.md |
| `docs/archive/superseded/frontend-roadmap.md` | Frontend task log | — | **KEEP** | Detailed execution log of completed frontend tasks |
| `docs/operations/runbooks/legacy-route-deprecation.md` | Legacy route policy | — | **KEEP** | Template policy; referenced by template docs |
| `docs/testing/load-and-concurrency.md` | Load testing | — | **KEEP** | Operational testing guide |
| `docs/security/malware-scanning.md` | Malware scan config | — | **KEEP** | CI/security operational doc |
| `docs/operations/runbooks/migration-rollback.md` | Migration rollback | — | **KEEP** | Referenced by .github/DEPLOY.md |
| `docs/mvp-pilot-deployment-checklist.md` | Pilot checklist | — | **KEEP** | Operational runbook |
| `docs/operations/observability.md` | Observability | — | **KEEP** | Operational reference |
| `docs/operations/backups/pitr.md` | Backup ops | — | **KEEP** | Operational runbook |
| `docs/platform-admin-model.md` | Admin model | — | **KEEP** | Referenced by .ai-rules/template-onboarding.md |
| `docs/operations/deployment.md` | Deployment (generic) | — | **KEEP** | Referenced by .ai-rules/docker.md and .ai-rules/template-onboarding.md; has note pointing to .github/DEPLOY.md |
| `docs/operations/runbooks/production-runtime.md` | Runtime examples | — | **KEEP** | Operational reference; cross-referenced |
| `docs/product/owner-acquisition.md` | Owner acquisition | — | **KEEP** | Product planning doc |
| `docs/product/owner-dashboard.md` | Dashboard planning | — | **KEEP** | Product planning doc |
| `docs/archive/superseded/staff-access-calendar-roadmap.md` | SAC execution plan | — | **KEEP** | Detailed execution cards for SAC epic |
| `docs/product/scope.md` | Product scope | Header says "not implemented unless in PROJECT_STATUS.md" — MVP is implemented | **UPDATE** | Update disclaimer and fix stale "call transfer remains planned" statement |
| `docs/product/public-demo.md` | Demo mode | — | **KEEP** | Accurate doc |
| `docs/architecture/redis-production-contract.md` | Redis contract | — | **KEEP** | Operational reference |
| `docs/operations/runbooks/membership-data-preflight.md` | SAC preflight | — | **KEEP** | Operational for SAC-001/002 |
| `docs/product/onboarding.md` | Pilot onboarding | — | **KEEP** | Operational runbook |
| `docs/security/secret-management.md` | Secret management | — | **KEEP** | Operational reference |
| `docs/specs/ivr-reschedule.md` | IVR reschedule spec | Implemented (P1-003) | **KEEP** | Historical spec; verifiable as implemented |
| `docs/specs/README.md` | Spec format guide | — | **KEEP** | Referenced by .ai-rules/context-map.md |
| `docs/specs/sac-002-membership-migration-runbook.md` | SAC-002 plan | — | **KEEP** | Future execution plan for SAC |
| `docs/specs/staff-access-and-calendar.md` | SAC spec | — | **KEEP** | Architecture spec for SAC epic |
| `docs/architecture/scaling.md` | Scaling benchmarks | — | **KEEP** | Operational benchmark reference |
| `docs/archive/legacy/template-onboarding.md` | Template onboarding | — | **KEEP** | Referenced by .ai-rules/documentation.md (table) |
| `docs/archive/legacy/template-usage.md` | Template usage | — | **KEEP** | Referenced by .ai-rules/context-map.md |
| `docs/architecture/tenant-isolation.md` | Tenancy patterns | — | **KEEP** | Referenced by .ai-rules/context-map.md |
| `docs/operations/troubleshooting.md` | Troubleshooting | — | **KEEP** | Operational reference |
| `docs/integrations/twilio.md` | Twilio runbook | — | **KEEP** | Operational runbook |
| `docs/architecture/webhook-idempotency.md` | Webhook patterns | — | **KEEP** | Operational reference |
| `docs/architecture/worker-reliability.md` | Worker reliability | — | **KEEP** | Operational reference |
| `frontend/README.md` | Frontend docs | — | **KEEP** | Frontend-specific reference |
| `observability/alertmanager/README.md` | Alertmanager config | — | **KEEP** | Config reference |
| `perf/README.md` | Perf testing | — | **KEEP** | Performance testing reference |

---

## 3. Missing Files (referenced but absent)

| File | Referenced by | Action |
|------|--------------|--------|
| `docs/learning/00-current-state-audit.md` | `.ai-rules/documentation.md`, `.ai-rules/context-map.md`, `AGENTS.md`, `CLAUDE.md` | Not created in this audit — learning-mode docs are created by the learning-mode workflow when a task uses mentor-style completion format. Out of scope for documentation cleanup. |

---

## 4. Target Documentation Structure

After this audit, the documentation set is:

```
README.md                       ← project entry point (updated)
PROJECT_STATUS.md               ← verified capabilities (updated)
ROADMAP.md                      ← high-level roadmap (updated 2026-06-27)
TECH_DEBT.md                    ← debt register (updated 2026-06-27)
docs/archive/legacy/template-freeze-checklist-root.md    ← template pointer (unchanged)
.github/DEPLOY.md               ← authoritative Railway deployment (unchanged)

docs/
├── CURRENT_STATE.md            ← full audit snapshot 2026-06-27 (new)
├── appointment-saas-roadmap.md ← executable backlog (unchanged)
├── product-scope.md            ← product scope (updated disclaimer)
├── domain-model.md             ← domain vocabulary (updated disclaimer)
├── demo-flow.md                ← local demo flow (endpoint paths fixed)
├── public-demo.md              ← demo mode config
├── ai-workflows.md             ← AI workflow reference (untouched)
├── two-agent-review-workflow.md← review workflow (untouched)
├── commands.md                 ← Makefile reference
├── ci-policy-guards.md         ← CI policy reference
├── tenant-isolation.md         ← tenancy patterns
├── file-upload-production.md   ← upload ops
├── migration-rollback.md       ← migration rollback
├── legacy-route-deprecation.md ← legacy route policy
├── platform-admin-model.md     ← admin model
├── production-deployment.md    ← deployment (generic, points to .github/DEPLOY.md)
├── production-runtime-examples.md
├── secret-management.md
├── observability-production.md
├── webhook-idempotency.md
├── worker-reliability.md
├── redis-production-contract.md
├── troubleshooting.md
├── template-onboarding.md      ← template clone guide
├── template-usage.md           ← template usage reference
├── sync-scaling-benchmark.md
├── load-concurrency-testing.md
├── malware-scanning.md
├── database-backup-restore.md
├── backup-restore-automation.md
├── pitr-and-scheduled-backups.md
├── mvp-pilot-deployment-checklist.md
├── adr/
│   ├── README.md               ← ADR index (all 8 ADRs listed)
│   ├── 0001-*.md through 0008-*.md
├── audits/
│   ├── documentation-audit-2026-06-27.md  ← this file
│   ├── AUDIT_CURRENT_REPO_STATE.md
│   ├── MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md
│   ├── p3-remaining-backlog-audit.md
│   ├── pre-p3-readiness-audit.md
│   └── staff-access-calendar-current-state.md
├── decisions/
│   └── README.md               ← ADR format guide (updated with ADRs 0002-0008)
├── frontend/
│   └── frontend-roadmap.md     ← completed frontend tasks log
├── foundation/
│   └── (historical template docs — unchanged)
├── product/
│   ├── owner-acquisition.md
│   ├── owner-dashboard.md
│   └── staff-access-calendar-roadmap.md
├── runbooks/
│   ├── membership-data-preflight.md
│   └── pilot-onboarding.md
└── specs/
    ├── README.md
    ├── ivr-reschedule.md
    ├── sac-002-membership-migration-runbook.md
    └── staff-access-and-calendar.md
```

---

## 5. Files Updated in This Audit

1. `README.md` — Node.js 20+ → 22+; Roadmap bullet list updated
2. `PROJECT_STATUS.md` — added pointer to `docs/project/current-state.md`; added post-June-22 completion notes
3. `docs/archive/superseded/decisions-readme.md` — added ADRs 0002-0008 to the index table
4. `docs/architecture/domain-model.md` — updated stale "not implemented" disclaimer
5. `docs/product/scope.md` — updated stale "not implemented" disclaimer; fixed "call transfer remains planned" claim
6. `docs/archive/superseded/demo-flow.md` — fixed IVR simulator endpoint paths (`/incoming` → `/call`, `/input` → `/press`)

## 6. Files Created in This Audit

- `docs/project/current-state.md` (new)
- `docs/audits/AUDIT_CURRENT_REPO_STATE.md` (new)
- `docs/audits/documentation-audit-2026-06-27.md` (this file)

## 7. Files Deleted in This Audit

None. All candidates for deletion are referenced by binding `.ai-rules/` files or have cross-references that cannot be broken.

---

## 8. Key Discrepancies Found (docs vs code)

| Discrepancy | File | Severity |
|------------|------|----------|
| Node.js requirement "20+" but package.json engines: `^22.13.0` | `README.md` | Medium |
| "call transfer remains planned work, not current runtime behavior" | `docs/product/scope.md` | Medium — call transfer IS implemented |
| "not database models implemented in the repository today" | `docs/architecture/domain-model.md` | Medium — all models ARE implemented |
| "not implemented unless verified by code and tests in PROJECT_STATUS.md" | `docs/architecture/domain-model.md`, `docs/product/scope.md` | Low — correct at time of writing, stale now |
| IVR simulator endpoint `/incoming` → actual `/call`; `/input` → actual `/press` | `docs/archive/superseded/demo-flow.md` | High — demo won't work with stale paths |
| ADR index only shows ADR 0001; ADRs 0002-0008 missing | `docs/archive/superseded/decisions-readme.md` | Low |
| `PROJECT_STATUS.md` verified as of 2026-06-22; P3-013/008/010/014, P4-004 done after that | `PROJECT_STATUS.md` | Medium |
| `docs/learning/00-current-state-audit.md` referenced by .ai-rules but directory missing | `.ai-rules/documentation.md` | Informational |
