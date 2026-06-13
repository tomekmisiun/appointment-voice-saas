# TDD and Regression

Complements `.ai-rules/testing.md` with **workflow** for bugs and new behavior.

## Bug fixes

When practical:

1. **Reproduce** — add a failing test that asserts correct behavior (or documents
   current bug).
2. **Verify failure** — run targeted pytest; confirm it fails for the expected
   reason.
3. **Fix minimally** — smallest change in the correct layer (usually service).
4. **Prove fix** — same test passes; run related module tests.
5. **Regression guard** — test stays in suite permanently.

Skip failing-test-first only when reproduction is prohibitively expensive (e.g.
full Compose E2E); document why and add the strongest feasible test.

## New behavior

| Area | Test expectation |
|------|------------------|
| New/changed route | API test via `TestClient`; status + envelope |
| Service logic | Unit or service-level test with db fixture |
| Auth / permissions | Positive and denial cases |
| Tenancy | Cross-tenant denial when data is tenant-scoped |
| Migrations | Upgrade path; downgrade rehearsal if destructive |
| Workers / queue | Job handler test; unknown type → DLQ when relevant |
| Security / rate limits | 401/403/429/503 as appropriate |
| Config validators | `tests/test_config.py` pattern for production guards |

## Must not

- Delete or skip tests to green CI without explicit user approval.
- Weaken assertions to pass (e.g. remove auth checks).
- Add tests that only assert mocks with no behavior claim.

## Commands

```bash
docker compose run --rm api pytest tests/test_<area>.py -v
make validate
```

Coverage floor: **85%** (`make validate`, CI).
