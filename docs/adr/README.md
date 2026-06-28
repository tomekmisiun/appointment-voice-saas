# Architecture Decision Records

Index of significant architecture decisions.

Use short, dated Markdown records with a status (`Proposed`, `Accepted`,
`Superseded`, or `Deprecated`), context, decision, consequences, and links to
the affected code or documentation.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-sync-vs-async-architecture.md) | Sync vs async API architecture | Accepted |
| [0002](0002-appointment-voice-saas-architecture.md) | Appointment Voice SaaS core architecture | Accepted |
| [0003](0003-recurring-staff-blocks.md) | Recurring staff/business blocks | Accepted |
| [0004](0004-deposits-and-payment-holds.md) | Deposits, payment holds, and refunds | Accepted |
| [0005](0005-calendar-conflict-import-spike.md) | Calendar conflict import spike | Accepted |
| [0006](0006-two-way-calendar-sync.md) | Two-way calendar sync | Accepted |
| [0007](0007-separate-staff-records-from-login-identities.md) | Separate staff records from login identities | Accepted |
| [0008](0008-external-busy-periods-as-availability-exclusions.md) | External busy periods as availability exclusions | Accepted |
| [0009](0009-public-readonly-demo.md) | Public read-only demo | Accepted |

ADR 0008 supersedes only ADR 0005 section 2 and ADR 0006 decision 1. Their
rejection of external booking authority and full bidirectional sync remains in
force.
