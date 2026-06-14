# Interview Defense Guide

Short answers grounded in **this repo's verified state**. Adjust if code drifted —
check `00-current-state-audit.md` first.

## Elevator pitch

"We forked a production FastAPI foundation into **Appointment Voice SaaS**. Today
we have a **multi-tenant backend** where a salon can define staff, services, hours,
compute **availability**, and **book appointments** with **DB-level double-booking
protection** and **audit logs**. Voice, SMS, and calendar are designed (ADR + roadmap)
but not shipped yet."

---

## Architecture questions

**Q: How is the code layered?**  
Routes in `app/api/routes` validate HTTP and auth; business logic lives in
`app/services`; SQLAlchemy models in `app/models`. Services raise domain errors,
not HTTP exceptions — mapped centrally in `exception_handlers.py`.

**Q: Why PostgreSQL as source of truth for bookings?**  
ADR 0002: external calendar/SMS are integrations. Bookings must stay correct if
a provider fails. We enforce overlaps with an `EXCLUDE USING gist` constraint, not
only Python checks.

**Q: How does multi-tenancy work?**  
Every product row has `tenant_id`. JWT carries tenant; services use `require_business`
and similar helpers so cross-tenant IDOR returns 404. Tests in
`test_product_tenant_isolation.py`.

---

## Security questions

**Q: How is auth handled?**  
JWT access + refresh; `token_version` on user invalidates old tokens; Redis stores
refresh `jti` for revocation. Rate limits on auth endpoints via Redis.

**Q: What fails closed?**  
Missing/invalid JWT → 401. Wrong role → 403. Production config validators refuse
weak secrets when `ENVIRONMENT=production`.

---

## DevOps / reliability questions

**Q: How do you test?**  
Pytest in Docker against real Postgres/Redis/MinIO; 85% coverage floor in CI.
Concurrency tests for booking races. Policy guards for migrations and CI regression.

**Q: Async work?**  
Redis lists in `job_queue.py`; `worker.py` processes jobs with retry + failed queue.
Password reset email and upload verification today; notification outbox planned.

**Q: Observability?**  
Structured logs with request IDs, Prometheus metrics on `/metrics`, health checks
for DB/Redis.

---

## Product / domain questions

**Q: What can a salon do in the API today?**  
CRUD business, staff, services, working hours, exceptions; query availability;
create/list/cancel bookings. Customer is deduped by phone internally — no standalone
customer API yet.

**Q: What's missing for the MVP demo in `docs/demo-flow.md`?**  
IVR simulation, SMS outbox/fake provider, calendar fake adapter, end-to-end smoke
scripts (EPIC E–J).

---

## Honest gaps (good to volunteer)

| Gap | Why it matters |
|-----|----------------|
| README vs audit doc | Use `00-current-state-audit.md` if README and code disagree |
| No notification outbox | Bookings don't trigger SMS yet |
| No IVR | Core product story unfinished |
| Working hours route tests missing | Partial test coverage |
| `app/main.py` still says "template" in OpenAPI summary | Cosmetic inconsistency |

---

## How to talk about AI/vibecoding in this repo

"We use `.ai-rules/` as binding law for agents, a **two-agent Builder/Reviewer**
workflow, CI policy guards, and learning docs under `docs/learning/`. Agents must
prove changes with `make validate` and explain mentor-style per `learning-mode.md`.
Human merges and branch protection stay in control."

---

## One-liners per EPIC (status)

| EPIC | One line |
|------|----------|
| B Domain | Done — models, APIs, tenant tests |
| C Availability | Done — slots, TZ, API |
| D Booking | Done — CRUD, EXCLUDE, audit |
| E Notifications | Not started |
| F Calendar | Not started |
| G IVR | Not started |

---

## Before an interview

1. Read `00-current-state-audit.md` (10 min).
2. Skim `03-request-flow-map.md` booking + auth flows.
3. Run `make validate` once locally and cite the passing pytest count from output.
