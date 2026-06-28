# Worker Reliability

This template uses Redis-backed background jobs for async work such as password
reset email delivery. The worker is designed to be safe under retries,
temporary failures, and multiple worker instances.

## Queue Model

Jobs move through these Redis structures:

- main queue: newly available jobs waiting for a worker
- processing queue: jobs currently being handled by a worker
- delayed queue: jobs waiting for retry backoff to expire
- failed queue: dead-letter jobs that exceeded retry limits

The worker promotes due delayed jobs, reclaims stale processing jobs after
`WORKER_PROCESSING_VISIBILITY_TIMEOUT_SECONDS`, dequeues with a processing
acknowledgement, acks successful jobs, schedules retries with exponential
backoff, and stores failure metadata when a job becomes a dead letter.

## Processing Visibility Timeout

When a worker dequeues a job, it moves into the processing queue with a
`processing_started_at` timestamp. If the worker crashes or is killed before
acking the job, a reaper returns stale processing jobs to the main queue after
`WORKER_PROCESSING_VISIBILITY_TIMEOUT_SECONDS` (default 300). Reclaimed jobs are
not treated as failures and do not increment `attempts`.

## Retry Backoff

Retry delay is calculated from the attempt count:

- base delay: `WORKER_RETRY_BACKOFF_BASE_SECONDS`
- maximum delay: `WORKER_RETRY_BACKOFF_MAX_SECONDS`

The delay grows exponentially until it reaches the configured maximum.

## Dead-Letter Metadata

Failed jobs store:

- `attempts`
- `last_error`
- `failed_at`
- original `payload`, `type`, and `request_id`

Inspect failed jobs with:

```bash
docker compose run --rm worker python -m app.worker_failed_jobs list
```

Requeue failed jobs manually when appropriate:

```bash
docker compose run --rm worker python -m app.worker_failed_jobs requeue
```

## Scheduler Locking

Scheduled maintenance uses a Redis lock so only one worker instance runs
maintenance during a given interval. Configure:

- `WORKER_MAINTENANCE_LOCK_KEY`
- `WORKER_MAINTENANCE_LOCK_TTL_SECONDS`
- `WORKER_MAINTENANCE_INTERVAL_SECONDS`

## Idempotency Guidance

Job handlers should be idempotent because retries and manual requeues can run
the same job more than once.

Recommended patterns for downstream projects:

- use a stable business key in the payload and enforce uniqueness in the
  database
- store a processed-job marker keyed by `job.id` or a domain idempotency key
- password-reset email jobs mark `password_reset_job_completed:{job_id}` in Redis
  after successful token persistence and email delivery
- make external side effects safe to repeat, such as upserts or provider calls
  guarded by unique request IDs
- keep password-reset style jobs safe by invalidating previous tokens before
  creating a new one

Do not assume that a job runs exactly once.

## Operational Checks

After worker changes or deployment:

- confirm the worker container is running
- verify Redis connectivity
- enqueue a test job and confirm it completes
- inspect failed jobs after induced errors
- confirm maintenance cleanup still runs on schedule
