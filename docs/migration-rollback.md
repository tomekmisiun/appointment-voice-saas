# Migration And Rollback Runbook

This template uses Alembic for database schema migrations. Production projects
should treat migrations as part of the deployment plan, not as an afterthought.

## Local Commands

Show the currently applied migration:

```bash
make migration-current
```

Show available migration heads:

```bash
make migration-heads
```

Apply all migrations:

```bash
make migration-upgrade
```

The direct command is:

```bash
docker compose run --rm api alembic upgrade head
```

## Deployment Order

Default release order:

1. Confirm CI is green.
2. Confirm a recent restorable database backup exists.
3. Deploy to staging.
4. Run `make migration-upgrade` or the equivalent deployment command in
   staging.
5. Run staging smoke checks.
6. Promote the same image to production.
7. Run production migrations.
8. Shift traffic to the new application version.
9. Verify readiness, logs, metrics, and core user flows.

## Expand/Contract Migrations

Use expand/contract migrations for changes that may break older code or require
data movement.

Expand release:

- add new nullable columns
- add new tables
- add indexes concurrently when the production database supports it
- keep old columns and old code paths working

Transition release:

- write to both old and new shapes when needed
- backfill existing data
- switch reads to the new shape after data is verified

Contract release:

- remove old code paths
- drop old columns or constraints
- clean up temporary compatibility code

Avoid mixing destructive schema changes with unrelated refactors.

## Data Backfills

For large data backfills:

- keep the migration small and reviewable
- prefer separate idempotent backfill commands or jobs
- batch work to avoid long locks
- log progress
- make the backfill restartable
- verify counts before switching reads

Do not hide large production data rewrites inside a normal request path.

## Failed Migration Handling

If a migration fails before application traffic is shifted:

1. Keep the old application version running.
2. Inspect the database migration state with `make migration-current`.
3. Fix the migration or create a forward-fix migration.
4. Re-run migrations in staging before trying production again.

If a migration fails after partial production rollout:

1. Stop further rollout.
2. Pause workers if they can write affected data.
3. Preserve logs and migration output.
4. Decide between forward fix, application rollback, or database restore.
5. Prefer a forward-fix migration when data is intact.
6. Use restore only for destructive or corrupted data states.

## Application Rollback

Application rollback is appropriate when:

- the database schema remains compatible with the previous image
- the problem is application behavior, not corrupted data
- the previous image is still available

Rollback steps:

1. Switch traffic back to the previous image.
2. Verify `GET /health/ready`.
3. Verify core auth and user flows.
4. Verify worker status.
5. Keep investigating the failed release.

## Database Rollback Policy

Do not rely on Alembic downgrade as the default production rollback strategy.

Preferred order:

1. Forward-fix migration.
2. Application rollback if schema remains compatible.
3. Restore from backup or point-in-time recovery when data integrity requires
   it.

Every destructive migration should explicitly document:

- what data may be removed
- how the change was backed up
- how restore would work
- whether application rollback remains possible

## Release Checklist

Before merging a schema-changing feature:

- migration file is committed
- migration is reviewable and focused
- `alembic upgrade head` passes
- tests pass against schema built from migrations
- README and `PROJECT_STATUS.md` are updated when behavior changes
- rollback or forward-fix path is known

Before production deploy:

- backup exists and restore process is known
- staging migration succeeded
- smoke checks passed
- previous image tag is available
- operators know whether worker processes should be paused

## Current Template Limits

This repository provides migration helper commands and a migration/rollback
runbook. It does not include provider-specific deployment automation,
zero-downtime migration enforcement, lock-time analysis, online schema change
tools, or automated rollback drills.
