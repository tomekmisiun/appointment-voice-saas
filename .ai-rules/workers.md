# Worker And Job Queue Rules

Background work uses Redis queues in `app/core/job_queue.py` and
`app/worker.py`.

## Job Handling

- MUST NOT acknowledge unknown job types as success. Route unknown types to the
  failed/DLQ path.
- MUST NOT remove `ack_job`, retry scheduling, processing-queue moves, or
  failed-queue handling without explicit user request.
- Password-reset and future job handlers MUST remain idempotent where completion
  markers or deduplication already exist.

## Redis And Queue Compatibility

- Redis backs rate limiting, refresh-token revocation, caching, idempotency
  locks, worker queues, and maintenance locks.
- MUST NOT rename default Redis queue names or key prefixes without explicit
  user request and a documented backward-compatibility or migration note.
- Queue-related settings MUST remain environment-driven through
  `app/core/config.py`.

## Tests

- Worker or queue changes MUST include or extend regression coverage in
  `tests/test_worker.py`, `tests/test_job_queue.py`, or related worker tests.
- MUST NOT merge worker changes with failing or skipped worker regression tests.
