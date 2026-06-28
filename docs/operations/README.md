# Operations

This page maps the active operational documents. It does not replace the
runbooks; use it as the entry point for production and pilot maintenance.

## Start Here

| Area | Current document |
|---|---|
| Configuration | [`configuration.md`](configuration.md) |
| Deployment | [`deployment.md`](deployment.md) |
| Observability | [`observability.md`](observability.md) |
| Troubleshooting | [`troubleshooting.md`](troubleshooting.md) |
| Backups | [`backups/overview.md`](backups/overview.md), [`backups/restore.md`](backups/restore.md), [`backups/pitr.md`](backups/pitr.md) |
| Migrations and rollback | [`runbooks/migration-rollback.md`](runbooks/migration-rollback.md) |
| Production runtime examples | [`runbooks/production-runtime.md`](runbooks/production-runtime.md) |
| File uploads | [`runbooks/file-uploads.md`](runbooks/file-uploads.md) |
| Legacy route deprecation | [`runbooks/legacy-route-deprecation.md`](runbooks/legacy-route-deprecation.md) |
| Membership data preflight | [`runbooks/membership-data-preflight.md`](runbooks/membership-data-preflight.md) |
| Pilot onboarding | [`../product/onboarding.md`](../product/onboarding.md) |
| Twilio | [`../integrations/twilio.md`](../integrations/twilio.md) |
| Secrets | [`../security/secret-management.md`](../security/secret-management.md) |
| Worker reliability | [`../architecture/worker-reliability.md`](../architecture/worker-reliability.md) |
| Redis | [`../architecture/redis-production-contract.md`](../architecture/redis-production-contract.md) |

## Operational Commands

Run from the repository root:

```bash
make migration-current
make migration-heads
make migration-upgrade
make db-backup
make db-restore-check
make smoke
make policy-guards
```

Backup and restore commands call shell scripts under [`../../scripts/`](../../scripts/).
Use dry-run targets before touching shared environments:

```bash
make db-backup-dry-run
make db-restore-check-dry-run
```

## Observability

Local observability is defined by:

- [`../../docker-compose.observability.yml`](../../docker-compose.observability.yml)
- [`../../observability/prometheus/`](../../observability/prometheus/)
- [`../../observability/grafana/`](../../observability/grafana/)
- [`../../observability/loki/`](../../observability/loki/)
- [`../../observability/alertmanager/`](../../observability/alertmanager/)

Metrics exist for HTTP requests, dependency checks, worker jobs, worker
maintenance, failed queue depth, integration reconciliation, SMS provider
requests, and calendar provider requests.

## Production Cautions

- Do not run migration or restore commands against production without an
  explicit operator plan and a verified backup.
- Production validators reject local defaults, weak secrets, missing webhook
  secrets, missing malware scan configuration, and unsafe host/rate-limit
  settings.
- `docker-compose.prod.yml` is not a full production platform; it requires
  external PostgreSQL, Redis, storage, TLS, and operational automation.
