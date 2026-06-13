# Scheduled Backups And PITR Checklist

This document complements `docs/backup-restore-automation.md` and
`docs/database-backup-restore.md`. The template does not operate your production
database provider. Each downstream project must configure backups, retention, and
point-in-time recovery (PITR) with the provider.

## Scheduled Backup Workflow

The repository includes `.github/workflows/scheduled-backup.yml` as an example
orchestration layer:

- **Schedule:** daily at `04:00 UTC` against the `production` GitHub environment
- **Manual runs:** `workflow_dispatch` with `staging` or `production`

The workflow delegates to `scripts/db_backup.sh` using environment-scoped secrets
and variables.

### Configure GitHub Environment

Add to `staging` and/or `production` environments:

| Type | Name | Purpose |
|------|------|---------|
| variable | `BACKUP_MODE` | `provider-hook` (default) or `direct` |
| variable | `BACKUP_FILE` | optional output path for direct dumps |
| secret | `BACKUP_HOOK_URL` | required for `provider-hook` |
| secret | `BACKUP_HOOK_TOKEN` | optional bearer token for the hook |
| secret | `DATABASE_URL` | required for `direct` mode |

Recommended split:

- **Production:** provider-managed backups through `provider-hook`, or `direct`
  only when your security model allows runner access to the database.
- **Staging:** manual `workflow_dispatch` rehearsals with `dry_run=true` first.

Dry run example:

```bash
gh workflow run scheduled-backup.yml \
  -f environment=staging \
  -f dry_run=true
```

When secrets are missing, the workflow exits successfully after logging that the
environment is not configured. This keeps the template forkable without live
provider credentials.

### Non-GitHub Schedules

For VM deployments, use cron on the host:

```cron
0 3 * * * cd /srv/fastapi-production-foundation && BACKUP_FILE=backups/nightly.dump make db-backup
```

For managed PostgreSQL, prefer the provider's native backup schedule over
runner-based `pg_dump` when possible.

## Restore Rehearsal

Backups are not production-ready until restores are rehearsed. Use:

- `make db-restore-check` locally
- `.github/workflows/backup-rehearsal.yml` manually or on a maintenance cadence

Rehearse after major migrations and before launch.

## PITR Provider Checklist

Point-in-time recovery is a **provider capability**, not template code. Before
launch, confirm these items with your database vendor runbook:

### Policy

- [ ] RPO target documented (maximum acceptable data loss window)
- [ ] RTO target documented (maximum acceptable downtime to restore)
- [ ] PITR retention window defined (for example 7, 14, or 35 days)
- [ ] Staging and production retention policies differ intentionally
- [ ] Legal/compliance retention requirements mapped to backup retention

### Provider Configuration

- [ ] Automated backups enabled on the production database instance
- [ ] PITR or WAL/archived log retention enabled where the provider supports it
- [ ] Backup storage region matches data residency requirements
- [ ] Backup encryption at rest verified (provider-managed or CMK)
- [ ] Cross-region backup copies configured if disaster recovery requires it
- [ ] Backup access restricted to break-glass roles

### Operational Readiness

- [ ] Documented restore owner and escalation path
- [ ] Restore runbook tested into an isolated non-production database
- [ ] Application smoke checks defined for post-restore validation
- [ ] Migration rollback policy coordinated with restore policy
- [ ] Incident checklist distinguishes logical restore vs PITR vs full rebuild
- [ ] Post-incident review captures backup/restore gaps

### Provider Examples (Documentation Only)

| Provider | Backup source of truth | PITR notes |
|----------|------------------------|------------|
| AWS RDS / Aurora | automated backups + optional snapshot sharing | enable PITR via backup retention; restore to new instance |
| Google Cloud SQL | automated backups | point-in-time restore to new instance or clone |
| Azure Database for PostgreSQL | geo-redundant backups depending on tier | verify PITR window per SKU |
| Neon / Supabase / Render | platform backup settings | confirm retention and restore target in vendor docs |
| Self-hosted PostgreSQL | `pg_basebackup`, WAL archiving, or volume snapshots | you own WAL retention, replay procedure, and monitoring |

The template's `provider-hook` mode is a trigger/integration point. It does not
replace provider backup configuration.

## What This Template Does Not Provide

- live backup storage or retention enforcement
- PITR execution against production
- automated verification that provider backups succeeded
- cross-provider disaster recovery architecture

Track those as downstream infrastructure decisions in your project runbook.

## Related Documents

- `docs/backup-restore-automation.md`
- `docs/database-backup-restore.md`
- `docs/migration-rollback.md`
- `docs/production-deployment.md`
