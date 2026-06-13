# Architecture Decisions

This template records significant architecture decisions as **ADRs**
(Architecture Decision Records).

## Canonical location

ADRs live in **`docs/adr/`**, not in this directory.

| ADR | Title |
|-----|-------|
| [0001](../adr/0001-sync-vs-async-architecture.md) | Sync vs async API architecture |

Index: [docs/adr/README.md](../adr/README.md)

## ADR format

Each ADR should include:

1. **Title** — short decision name
2. **Status** — Proposed | Accepted | Deprecated | Superseded
3. **Context** — forces, constraints, template scope
4. **Decision** — what we chose
5. **Alternatives considered** — brief list with why rejected
6. **Consequences** — positive, negative, follow-ups for forks

Use numbered files: `docs/adr/0002-<slug>.md`.

## When to write an ADR

- Template-wide architectural direction (sync vs async, tenancy model, queue design)
- Decisions that forks will ask about repeatedly
- Trade-offs that are **not** obvious from code alone

Do **not** write ADRs for routine feature work — use `docs/specs/` instead.

## Agent workflow

- Read existing ADRs before large architectural changes
- Propose a new ADR when changing a previously accepted decision
- Link ADRs from `docs/ai-workflows.md` and relevant `docs/` runbooks
