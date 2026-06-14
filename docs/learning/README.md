# Learning Documentation Index

Code-verified maps and guides for understanding this repository. Start here if
you are onboarding, defending the project in an interview, or steering AI agents.

## Read first

1. **[`00-current-state-audit.md`](00-current-state-audit.md)** — what is **actually**
   implemented vs planned (ground truth from code, tests, migrations).
2. **[`01-system-mental-map.md`](01-system-mental-map.md)** — layers and directories.
3. **[`03-request-flow-map.md`](03-request-flow-map.md)** — how HTTP and worker
   requests move through the stack.

Then pick by task: file lookup → `02`, domain → `04`, how to change → `05`,
interviews → `06`.

## Each file

| File | Type | Purpose |
|------|------|---------|
| `00-current-state-audit.md` | **Code-verified truth** | Implementation status tables, test map, doc drift notes |
| `01-system-mental-map.md` | Explanatory guide | Architecture diagram, folder roles |
| `02-file-by-file-map.md` | Explanatory guide | Important files, routes, services, tests |
| `03-request-flow-map.md` | Explanatory guide | Auth, booking, webhook, worker, CI flows |
| `04-domain-model-map.md` | Explanatory guide (entities from code) | Business/booking ER view; cross-check `00` |
| `05-how-to-change-common-things.md` | Explanatory guide | Safe change playbooks + validation commands |
| `06-interview-defense-guide.md` | Explanatory guide | Short answers for technical interviews |

**Code-verified truth** = derived from routes, models, migrations, and tests at
audit time. **Explanatory guides** teach structure and process; verify claims
against `00` before citing in reviews or interviews.

## When to refresh `00-current-state-audit.md`

**Binding rule** (see `.ai-rules/documentation.md`):

- **MUST** update `00-current-state-audit.md` in the **same change set** when you
  mark a roadmap item `[x]` in `docs/appointment-saas-roadmap.md` or add/remove
  verified capabilities in `PROJECT_STATUS.md`.
- **MUST** update when product routes, models, migrations, or primary tests are
  added or removed (even if roadmap row is unchanged).
- After refresh: run `make validate-ai-workflows`; run `make validate` when the
  change claims runtime behavior.

Do not copy roadmap prose into `00` without code verification.

## Related rules

- Agent mentor format: `.ai-rules/learning-mode.md`
- Doc accuracy: `.ai-rules/documentation.md`
