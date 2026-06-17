# Production Observability

This template exposes Prometheus metrics, structured logs, optional Sentry error
tracking, and a local observability stack. Production deployments should treat
metrics and traces as per-instance signals that are aggregated externally.

## Metrics Model

The API exposes Prometheus metrics from `/metrics`. The worker exposes the same
Prometheus text format from a dedicated HTTP server (default `:9100/metrics`).

Production defaults:

- `METRICS_REQUIRE_AUTH` defaults to `true` when `ENVIRONMENT=production`
- set `METRICS_BEARER_TOKEN` to a long random secret and scrape with
  `Authorization: Bearer <token>`
- restrict network access to `/metrics` (internal load balancer, private subnet,
  or sidecar scrape) even when bearer auth is enabled

Core HTTP metrics:

- `http_requests_total`
- `http_request_duration_seconds`

Worker metrics:

- `worker_jobs_total{job_type,status}`
- `worker_maintenance_runs_total{status}`
- `worker_failed_queue_depth` — number of jobs currently sitting in the
  dead-letter queue (exhausted retries), refreshed on every maintenance tick

Dependency metrics:

- `dependency_checks_total{dependency,status}`
- `dependency_health_status{dependency}`

Application metadata:

- `app_info{service,environment,instance_id?}`

## Multi-Process And Multi-Instance Deployments

Use one of these patterns:

- **Multiple replicas/instances**: configure `METRICS_INSTANCE_ID` per replica
  and scrape each instance separately. Aggregate in Prometheus/Grafana with
  `sum(...) by (...)` queries.
- **Multiple Uvicorn workers in one container**: set `PROMETHEUS_MULTIPROC_DIR`
  to a writable directory shared by all worker processes. The metrics endpoint
  will aggregate process-local counters and histograms safely.

Example production environment variables:

```text
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
METRICS_INSTANCE_ID=api-1
```

Create the directory before starting the process and ensure it is writable by the
runtime user.

## Alert Routing

Local alert rules live in `observability/prometheus/rules`. They cover:

- target availability
- 5xx error rate
- p95 latency
- worker dead-letter queue backlog (`WorkerFailedQueueBacklog`, fires when
  `worker_failed_queue_depth > 0` for 15 minutes — exhausted jobs are silent
  async data loss until someone notices)
- worker job failure rate (`WorkerJobFailureRate`, fires on any
  `worker_jobs_total{status="failed"}` in the last 15 minutes)

Production projects should route Alertmanager notifications to real on-call
destinations such as email, Slack, PagerDuty, or an incident platform. Keep
alert thresholds environment-specific and tune them after observing baseline
traffic.

Recommended production checks:

- scrape success for every API replica
- elevated 5xx rate
- elevated p95 latency
- worker job failure rate via `worker_jobs_total{status="failed"}`
- worker dead-letter queue depth via `worker_failed_queue_depth`
- dependency health gauges at zero

## Trace And Error Correlation

When `SENTRY_DSN` is configured, the application sends errors and optional
traces to Sentry. Request IDs are attached to Sentry events through:

- the `request_id` tag
- the `contexts.request.request_id` field

Use the same request ID in logs to correlate API failures, worker retries, and
external error reports.

For broader distributed tracing, evaluate OpenTelemetry or a provider-native
tracing stack in the downstream project. This template intentionally keeps
tracing optional and environment-driven.

## Operational Checks

After deployment:

- verify `/metrics` on every API replica
- verify `worker:9100/metrics` (or your configured `WORKER_METRICS_PORT`) when the
  worker runs as a separate process
- confirm logs include `request_id`
- confirm Sentry receives a test event with request correlation when enabled
- confirm Alertmanager routes alerts to the expected destination
