# Backup And Restore Automation

This template ships provider-neutral backup and restore rehearsal automation that
can run locally, against direct PostgreSQL connection strings, or through a
provider hook.

## Scripts

Local Docker Compose backup:

```bash
make db-backup
```

Local restore rehearsal with core-table verification:

```bash
make db-restore-check
```

Dry-run planning without touching the database:

```bash
make db-backup-dry-run
make db-restore-check-dry-run
```

Underlying scripts:

- `scripts/db_backup.sh`
- `scripts/db_restore_rehearsal.sh`

## Backup Modes

`scripts/db_backup.sh` supports:

| Mode | Purpose |
|------|---------|
| `local-docker` | Default. Uses `docker compose exec` and `pg_dump`. |
| `direct` | Uses `pg_dump` against `DATABASE_URL` or `PGDATABASE`. |
| `provider-hook` | POSTs to `BACKUP_HOOK_URL` to trigger provider-managed backups. |

Examples:

```bash
BACKUP_MODE=direct DATABASE_URL="$DATABASE_URL" bash scripts/db_backup.sh
```

```bash
BACKUP_MODE=provider-hook \
  BACKUP_HOOK_URL="https://ops.example.test/backups/trigger" \
  BACKUP_HOOK_TOKEN="$BACKUP_HOOK_TOKEN" \
  DRY_RUN=true \
  bash scripts/db_backup.sh
```

## Restore Rehearsal Modes

`scripts/db_restore_rehearsal.sh` supports:

| Mode | Purpose |
|------|---------|
| `local-docker` | Default. Restores into `RESTORE_CHECK_DB`, verifies core tables, drops temp DB. |
| `direct` | Restores using `RESTORE_ADMIN_DATABASE_URL` or `DATABASE_URL` admin connection. |

The rehearsal verifies:

- basic SQL connectivity
- presence of core tables such as `tenants`, `users`, and `alembic_version`

Verification SQL is generated from `app/ops/restore_verification.py`.

## Provider Examples

### Managed PostgreSQL (RDS, Cloud SQL, Neon, Supabase)

Use the provider's automated backup feature as the source of truth. Schedule a
regular restore rehearsal into an isolated non-production database and run
application smoke checks against that target.

Hook-based trigger example:

```bash
BACKUP_MODE=provider-hook \
  BACKUP_HOOK_URL="https://ops.example.test/hooks/database-backup" \
  bash scripts/db_backup.sh
```

### VM + Docker Compose

Use cron on the host:

```cron
0 3 * * * cd /srv/fastapi-production-foundation && BACKUP_FILE=backups/nightly.dump make db-backup
30 3 * * 1 cd /srv/fastapi-production-foundation && make db-restore-check
```

### GitHub Actions

Use `.github/workflows/backup-rehearsal.yml` for manual or scheduled restore
rehearsals in CI-like environments.

Use `.github/workflows/scheduled-backup.yml` as a daily provider-hook or direct
backup example against GitHub environment secrets. See
`docs/pitr-and-scheduled-backups.md` for configuration and the PITR checklist.

## Operational Guidance

- keep backups out of git
- rehearse restores before launch and after major schema changes
- prefer provider point-in-time recovery for production incidents
- treat restore rehearsals as production readiness checks, not optional docs

See also:

- `docs/database-backup-restore.md`
- `docs/migration-rollback.md`
- `docs/production-deployment.md`
