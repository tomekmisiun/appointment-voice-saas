# Database Backup And Restore Runbook

This template uses PostgreSQL as the primary database. Every production project
built from this template must define and rehearse a backup and restore process
before launch.

## Local Backup

Create a local custom-format PostgreSQL dump from the Docker Compose database:

```bash
make db-backup
```

The Makefile delegates to `scripts/db_backup.sh`. See
`docs/backup-restore-automation.md` for direct-connection and provider-hook
modes.

Default output:

```text
backups/app_db.dump
```

The `backups/` directory and common dump file extensions are ignored by git.
Do not commit database dumps.

Override defaults when needed:

```bash
make db-backup BACKUP_FILE=backups/manual.dump DB_NAME=app_db
```

## Local Restore Rehearsal

Verify that a dump can be restored into a temporary database:

```bash
make db-restore-check
```

The restore rehearsal script verifies core tables such as `tenants`, `users`,
and `alembic_version` before dropping the temporary database.

The restore check:

1. verifies that `BACKUP_FILE` exists
2. drops the temporary restore-check database if it already exists
3. creates a fresh temporary restore-check database
4. restores the dump into that database
5. runs a simple SQL smoke check
6. drops the temporary restore-check database

Default temporary database:

```text
app_restore_check
```

Override it if needed:

```bash
make db-restore-check RESTORE_CHECK_DB=app_restore_check_2
```

## Production Expectations

Production backups should be handled by the database provider or deployment
platform, not by ad hoc shell access alone.

Document these values for every real project:

- backup mechanism
- backup frequency
- retention period
- encryption at rest
- backup storage location
- recovery point objective
- recovery time objective
- restore target
- restore rehearsal cadence
- person or team responsible for restores

Minimum baseline:

- Automated backups are enabled before launch.
- Backups are encrypted at rest.
- Backup access is limited to operators who need it.
- At least one restore rehearsal is completed before production launch.
- Restore rehearsals are repeated after major database changes.

## Restore Drill

Use this drill before launch and periodically after launch:

1. Select a recent backup.
2. Restore it to an isolated non-production database.
3. Run migrations if the restore target is expected to be upgraded.
4. Run smoke checks against the restored database.
5. Verify key tables and row counts.
6. Confirm sensitive data handling rules for the restored environment.
7. Record the restore duration and any manual steps.

Do not restore production data into an insecure local environment.

## Incident Restore Guidance

During an incident:

1. Identify whether the issue requires a restore or a forward fix.
2. Stop workers if they may continue writing bad data.
3. Preserve the current database state for investigation if possible.
4. Restore to a new database when the platform supports it.
5. Point the application to the restored database only after validation.
6. Run readiness checks and application smoke checks.
7. Document the incident, restore point, data loss window, and follow-up work.

Prefer provider-supported point-in-time recovery when available.

## Current Template Limits

This repository provides local backup and restore rehearsal commands plus
provider-neutral automation scripts and a manual GitHub Actions workflow. It
does not include provider-specific snapshot scheduling, cross-region replication,
point-in-time recovery setup, or automated production restore into live
environments.

See `docs/backup-restore-automation.md` for provider examples and automation
patterns.
