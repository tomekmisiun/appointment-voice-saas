# Incremental Work

Implement changes as **thin vertical slices** with frequent validation.

## Rules

1. **One slice at a time** — e.g. migration → service → route → test, not all
   layers in one untested batch.
2. **Test after each slice** — run targeted pytest for touched modules before
   full `make validate`.
3. **Do not mix unrelated concerns** — no feature + refactor + unrelated docs in
   the same commit unless the user explicitly asked.
4. **Keep diffs reviewable** — prefer several small commits on a branch over one
   large unreadable diff (user still controls when to commit).
5. **Stop at scope boundary** — if you discover extra debt, note it; do not fix
   unless in scope.

## Suggested slice order (features)

1. Model + Alembic migration (+ migration test if downgrade risk)
2. Schemas (request/response)
3. Service functions (domain errors, no `HTTPException`)
4. Route + permissions + dependencies
5. Integration tests (API client)
6. Docs / tracking files

## Refactors

- Behavior-preserving refactors: run existing tests after each step.
- MUST NOT combine refactor with behavior change in the same slice.

## Validation cadence

```bash
# After a slice touching tests/app
docker compose run --rm api pytest tests/test_<module>.py -q

# Before declaring done
make validate
```

Documentation-only or AI-rules-only slices: `make validate-ai-workflows` and
`make policy-guards` as applicable.
