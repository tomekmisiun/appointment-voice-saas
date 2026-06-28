# Testing

The repository has backend pytest coverage, frontend Vitest coverage, policy
guards, load smoke profiles, and CI workflows. There is no Playwright or Cypress
browser E2E suite in this branch.

## Backend

Run the full local validation suite from the repository root:

```bash
make validate
```

This runs Ruff and pytest with coverage inside Docker Compose:

- `docker compose run --rm api ruff check .`
- `docker compose run --rm api pytest --cov=app --cov-report=term-missing --cov-fail-under=85 -v`

Other backend commands:

```bash
make test
make test-parallel
make test-coverage
```

`make test` uses `docker compose exec api`, so the API container must already be
running. `make validate` uses `docker compose run --rm api`.

## Frontend

Run from `frontend/`:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm api:check
```

The frontend uses Vitest, React Testing Library, MSW, TypeScript, ESLint, and
Next.js production build validation.

## Policy And Workflow Checks

Run from the repository root:

```bash
make policy-guards
make validate-ai-workflows
```

Policy guards verify repository rules such as migration/model pairing,
dangerous migration operations, lockfile pairing, CI gate regression, and
commit-message attribution policy.

## Load Smoke

Run from the repository root with Docker Compose available:

```bash
make load-smoke-ci
make load-validate
```

The load profiles call `perf.load_baseline` against health/readiness/auth
profiles. See [`load-concurrency-testing.md`](load-and-concurrency.md) and
[`perf/README.md`](../../perf/README.md).

## CI Coverage

`.github/workflows/ci.yml` currently includes:

| Job | Scope |
|---|---|
| `pre-commit` | pre-commit hooks with uv-managed dev dependencies. |
| `policy-guards` | repository policy scripts. |
| `secrets-scan` | gitleaks. |
| `test` | backend pytest with xdist, coverage, backup/restore rehearsal. |
| `load-smoke` | health load threshold smoke. |
| `docker-build` | production image build, dev dependency exclusion, Trivy. |
| `frontend-validate` | pnpm install, lint, typecheck, Vitest, Next build. |
| `public-demo-contract` | public demo backend contract tests. |
| `deploy-production` | Railway deploy after all required jobs pass on `main`. |

## Test Limitations

- Browser E2E coverage is not implemented.
- Production smoke after Railway deploy is not currently a post-deploy CI gate.
- Some current-state counts in historical documents were point-in-time audit
  results; do not rely on static test counts unless rerun.

