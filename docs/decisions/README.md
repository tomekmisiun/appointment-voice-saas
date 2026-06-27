# Architecture Decisions

This template records significant architecture decisions as **ADRs**
(Architecture Decision Records).

## Canonical location

ADRs live in **`docs/adr/`**, not in this directory.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](../adr/0001-sync-vs-async-architecture.md) | Sync vs async API architecture | Accepted |
| [0002](../adr/0002-appointment-voice-saas-architecture.md) | Appointment Voice SaaS core architecture | Accepted |
| [0003](../adr/0003-recurring-staff-blocks.md) | Recurring staff/business blocks | Accepted |
| [0004](../adr/0004-deposits-and-payment-holds.md) | Deposits, payment holds, and refunds | Accepted |
| [0005](../adr/0005-calendar-conflict-import-spike.md) | Calendar conflict import spike | Accepted |
| [0006](../adr/0006-two-way-calendar-sync.md) | Two-way calendar sync | Accepted |
| [0007](../adr/0007-separate-staff-records-from-login-identities.md) | Separate staff records from login identities | Accepted |
| [0008](../adr/0008-external-busy-periods-as-availability-exclusions.md) | External busy periods as availability exclusions | Accepted |

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
