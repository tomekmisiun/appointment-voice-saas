# Documentation Index

This is the active documentation map for VoxSlot / Appointment Voice SaaS.
Archived material lives under [`archive/`](archive/) and is not a source of
truth for current behavior.

## Start Here

| Document | Purpose |
|---|---|
| [`../README.md`](../README.md) | Project overview, quick start, status summary, and main links. |
| [`project/current-state.md`](project/current-state.md) | Code-verified implementation snapshot and known limitations. |
| [`development/commands.md`](development/commands.md) | Makefile command reference. |
| [`operations/troubleshooting.md`](operations/troubleshooting.md) | Local setup, test, worker, upload, Redis, and CI troubleshooting. |

## Project State

| Document | Purpose |
|---|---|
| [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) | Current verified capability summary. |
| [`../ROADMAP.md`](../ROADMAP.md) | High-level future work and execution order. |
| [`../TECH_DEBT.md`](../TECH_DEBT.md) | Active technical debt and product gap register. |
| [`project/implementation-backlog.md`](project/implementation-backlog.md) | Detailed executable backlog that remains open. |

## Product

| Document | Purpose |
|---|---|
| [`product/scope.md`](product/scope.md) | Product problem, users, non-goals, and assumptions. |
| [`product/public-demo.md`](product/public-demo.md) | Public read-only demo contract and configuration. |
| [`product/onboarding.md`](product/onboarding.md) | Manual pilot onboarding procedure. |
| [`product/owner-acquisition.md`](product/owner-acquisition.md) | Pilot-owner acquisition and lead-intake flow. |
| [`product/owner-dashboard.md`](product/owner-dashboard.md) | Owner dashboard MVP scope and API gaps. |

## Architecture

| Document | Purpose |
|---|---|
| [`architecture/overview.md`](architecture/overview.md) | Current components, boundaries, request flows, persistence, and integrations. |
| [`architecture/domain-model.md`](architecture/domain-model.md) | Product entities and relationships implemented in the backend. |
| [`architecture/tenant-isolation.md`](architecture/tenant-isolation.md) | Tenant and business isolation expectations. |
| [`architecture/webhook-idempotency.md`](architecture/webhook-idempotency.md) | Webhook verification and idempotency guarantees. |
| [`architecture/worker-reliability.md`](architecture/worker-reliability.md) | Queue, retry, dead-letter, scheduler, and worker reliability behavior. |
| [`architecture/redis-production-contract.md`](architecture/redis-production-contract.md) | Redis production requirements and failure semantics. |
| [`architecture/platform-admin-model.md`](architecture/platform-admin-model.md) | Current platform-admin model and production options. |
| [`architecture/scaling.md`](architecture/scaling.md) | Sync route scaling benchmark notes. |

## API

| Document | Purpose |
|---|---|
| [`api/overview.md`](api/overview.md) | API conventions, route groups, authentication, webhooks, and OpenAPI reference. |

## Operations

| Document | Purpose |
|---|---|
| [`operations/README.md`](operations/README.md) | Operational index for deployment, backup, observability, and runbooks. |
| [`operations/configuration.md`](operations/configuration.md) | Backend, frontend, production, and observability configuration sources. |
| [`operations/deployment.md`](operations/deployment.md) | Supported Railway deployment path and production release boundaries. |
| [`operations/observability.md`](operations/observability.md) | Production metrics, logs, alert routing, traces, and operational checks. |
| [`operations/troubleshooting.md`](operations/troubleshooting.md) | Troubleshooting guide for local and production-like failures. |
| [`operations/backups/overview.md`](operations/backups/overview.md) | Backup and restore automation overview. |
| [`operations/backups/restore.md`](operations/backups/restore.md) | Database backup and restore runbook. |
| [`operations/backups/pitr.md`](operations/backups/pitr.md) | Scheduled backups and PITR checklist. |
| [`operations/runbooks/migration-rollback.md`](operations/runbooks/migration-rollback.md) | Migration and rollback runbook. |
| [`operations/runbooks/production-runtime.md`](operations/runbooks/production-runtime.md) | Self-managed production runtime examples. |
| [`operations/runbooks/file-uploads.md`](operations/runbooks/file-uploads.md) | File upload production safety runbook. |
| [`operations/runbooks/legacy-route-deprecation.md`](operations/runbooks/legacy-route-deprecation.md) | Legacy unversioned route deprecation policy. |
| [`operations/runbooks/membership-data-preflight.md`](operations/runbooks/membership-data-preflight.md) | Membership data preflight procedure. |

## Integrations

| Document | Purpose |
|---|---|
| [`integrations/twilio.md`](integrations/twilio.md) | Twilio credential, webhook, signature, rate-limit, and incident-response runbook. |

## Testing

| Document | Purpose |
|---|---|
| [`testing/README.md`](testing/README.md) | Backend, frontend, policy, load, and CI validation commands. |
| [`testing/load-and-concurrency.md`](testing/load-and-concurrency.md) | Load smoke profiles and concurrency coverage. |

## Security

| Document | Purpose |
|---|---|
| [`security/overview.md`](security/overview.md) | Security model, secrets, auth, webhook protection, demo limits, and risk register links. |
| [`security/secret-management.md`](security/secret-management.md) | Secret inventory and rotation guidance. |
| [`security/malware-scanning.md`](security/malware-scanning.md) | Malware scanner integration boundary. |

## Development

| Document | Purpose |
|---|---|
| [`development/commands.md`](development/commands.md) | Makefile command reference. |
| [`development/ci-policy.md`](development/ci-policy.md) | CI and pre-commit policy guard reference. |
| [`development/workflows/ai-workflows.md`](development/workflows/ai-workflows.md) | AI-assisted workflow guide for this repository. |
| [`development/workflows/two-agent-review.md`](development/workflows/two-agent-review.md) | Builder/reviewer workflow. |

## ADR

| Document | Purpose |
|---|---|
| [`adr/README.md`](adr/README.md) | Architecture Decision Record index and format. |

## Specifications

| Document | Purpose |
|---|---|
| [`specs/README.md`](specs/README.md) | Feature specification conventions. |
| [`specs/ivr-reschedule.md`](specs/ivr-reschedule.md) | IVR reschedule feature specification. |
| [`specs/sac-002-membership-migration-runbook.md`](specs/sac-002-membership-migration-runbook.md) | SAC-002 membership migration plan. |
| [`specs/staff-access-and-calendar.md`](specs/staff-access-and-calendar.md) | Staff access, scheduling, and calendar integration specification. |

## Archive

| Document | Purpose |
|---|---|
| [`archive/README.md`](archive/README.md) | Index of historical, superseded, completed, and legacy documentation. |
