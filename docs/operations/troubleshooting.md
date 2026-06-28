# Local Troubleshooting

Common issues when running the template with Docker Compose and uv.

## Stack does not start

Symptoms:

- `docker compose up` exits immediately for a service.
- API container restarts in a loop.

Checks:

1. Confirm Docker is running and ports `8000`, `5432`, `5433`, `6379`, `9000`, and
   `9001` are free.
2. Verify `.env` exists and includes a non-placeholder `SECRET_KEY`.
3. Inspect service logs:

   ```bash
   docker compose logs api
   docker compose logs db
   docker compose logs redis
   docker compose logs minio
   ```

## `SECRET_KEY` validation errors

The application rejects known weak values such as `change-me` and very short
production secrets.

Fix:

1. Copy `.env.example` to `.env` if needed.
2. Set `SECRET_KEY` to a long random value.
3. Restart the stack:

   ```bash
   docker compose up --build -d
   ```

## Database or migration errors

Symptoms:

- API fails on startup with database connection errors.
- Admin commands report missing tables.

Checks:

1. Ensure `db` is healthy:

   ```bash
   docker compose ps
   ```

2. Apply migrations:

   ```bash
   make migration-upgrade
   ```

3. Confirm the current revision:

   ```bash
   make migration-current
   ```

## Tests fail locally

Symptoms:

- `make test` or `make validate` fails inside Docker.
- Redis or MinIO connection errors appear in pytest output.

Checks:

1. Run tests in a one-off API container so dependencies start automatically:

   ```bash
   docker compose run --rm api pytest -v
   ```

2. Rebuild the API image after dependency changes:

   ```bash
   docker compose build api
   ```

3. If only rate-limit tests fail, confirm Redis is reachable from the API
   container.

## Smoke checks fail

Symptoms:

- `make smoke` cannot reach the API or login fails.

Checks:

1. Start the stack and apply migrations:

   ```bash
   make bootstrap
   ```

2. Confirm the API responds:

   ```bash
   curl http://localhost:8000/health
   ```

3. Seed development users before smoke testing:

   ```bash
   make seed
   ```

4. Override the API URL when the app runs on a different host or port:

   ```bash
   API_BASE_URL=http://127.0.0.1:8000 make smoke
   ```

## File upload failures

Symptoms:

- Upload endpoints return `503` or storage errors.

Checks:

1. Confirm MinIO is running:

   ```bash
   docker compose ps minio
   ```

2. Verify S3 settings in `.env` match the local Compose defaults.
3. Check API logs for bucket initialization or credential errors.

## Worker jobs do not run

Symptoms:

- Password reset emails are enqueued but never processed.

Checks:

1. Confirm the worker service is running:

   ```bash
   docker compose ps worker
   ```

2. Inspect worker logs:

   ```bash
   docker compose logs worker
   ```

3. List failed jobs when needed:

   ```bash
   docker compose run --rm worker python -m app.worker_failed_jobs list
   ```

## Redis connectivity or auth refresh failures in production

Symptoms:

- `/health/ready` fails while PostgreSQL is healthy.
- `/auth/refresh` returns `401` or `500` spikes during Redis maintenance.
- Worker stops dequeuing jobs.

Checks:

1. Hit `GET /health/redis` on the API instance.
2. Verify production Redis host, password, TLS, and network ACLs match
   `docs/operations/deployment.md`.
3. Review HA/failover behavior against `docs/architecture/redis-production-contract.md`
   (refresh rotation is fail-closed when Redis cannot record revocations).

## CI or pre-commit policy guard failures

See `docs/development/ci-policy.md` for what CI and pre-commit enforce, how to run
guards locally (`make policy-guards`), and approved bypass mechanisms.
