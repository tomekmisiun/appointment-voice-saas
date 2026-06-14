# How to Change Common Things (safely)

Manual playbook for backend learners. Always run `make validate` after app/test
changes.

## Add a new API endpoint

1. **Schema** — `app/schemas/<resource>.py` (request + response).
2. **Service** — business logic in `app/services/<resource>_service.py`; raise
   `DomainError` subclasses.
3. **Route** — thin handler in `app/api/routes/<resource>.py`; use
   `Depends(get_current_user)` / `require_role`.
4. **Register** — include router in `app/api/v1.py` if new module.
5. **Tests** — `tests/test_<resource>.py`; include auth denial + tenant isolation
   if product-scoped.
6. **OpenAPI** — error responses via patterns in `app/api/openapi.py` if admin route.

**Break risks:** forgetting `tenant_id` filter; `HTTPException` in service; missing tests.

---

## Add or change a database column

1. Edit model in `app/models/`.
2. `docker compose run --rm api alembic revision --autogenerate -m "..."` — **review**
   generated file; never blind-commit autogen.
3. Ensure `upgrade()` is additive; destructive drops need `allow-migration-drops` entry
   (see `docs/ci-policy-guards.md`).
4. Update Pydantic schemas if exposed via API.
5. Run `make validate` (includes migration tests).

**Break risks:** CI policy guard; prod deploy without migrate; ORM/schema drift.

---

## Change booking or availability behavior

| Change | Touch |
|--------|-------|
| Slot rules | `availability_service.py`, `test_availability.py` |
| Booking rules | `booking_service.py`, `test_bookings.py` |
| Concurrency | `2b3c4d5e6f7a` constraint + `test_concurrency.py` |
| Audit | `audit_log_service.py`, `booking_service.py`, `test_booking_audit.py` |

Always keep **tenant + business** scoping in `require_*` calls.

---

## Add a background job

1. Define job type string constant (see `password_reset_service.py` pattern).
2. Enqueue via `job_queue.enqueue_job` from service.
3. Register handler branch in `app/worker.py` `handle_job()` (if/elif on job type).
4. Test with `tests/test_worker.py` or dedicated test.

**Break risks:** unknown job type acked as success (forbidden by `.ai-rules/workers.md`).

---

## Change auth or permissions

Files: `dependencies/auth.py`, `core/security.py`, `core/permissions.py`, routes.

Run: `tests/test_auth.py`, `tests/test_permissions.py`, `tests/test_access_token_revocation.py`.

**Break risks:** fail-open routes; refresh token bypass.

---

## Update documentation status

| File | Rule |
|------|------|
| `PROJECT_STATUS.md` | Verified facts only — see § Verified Capabilities |
| `README.md` | Setup/API/workflow changes |
| `docs/appointment-saas-roadmap.md` | Mark `[x]` only when done |

After doc/rules-only edits: `make validate-ai-workflows` + `make policy-guards`.

Do **not** copy roadmap text into PROJECT_STATUS without tests.

---

## Local validation commands

| Scope | Command |
|-------|---------|
| Full app | `make validate` (~2 min, Docker) |
| One test file | `docker compose run --rm api pytest tests/test_bookings.py -v` |
| AI/rules/docs | `make validate-ai-workflows` + `make policy-guards` |
| Pre-commit | `uv run pre-commit run --all-files` |

---

## Git / CI gotchas (learned from this repo)

1. New migration with `op.drop_*` in **`upgrade()`** → needs `allow-migration-drops` or CI fails.
2. `op.drop_*` in **`downgrade()`** only → OK after policy fix (2026-06).
3. Model change without migration → CI fails `model-migration-pair`.
4. AI commit trailers → `make policy-guards` fails.

---

## Agent completion checklist

After your change, produce sections from `.ai-rules/learning-mode.md` (mentor
format). Run Reviewer subagent for non-trivial code changes.
