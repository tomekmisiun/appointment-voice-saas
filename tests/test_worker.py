from app.core.job_queue import (
    Job,
    dequeue_job,
    enqueue_job,
    list_failed_jobs,
    move_job_to_failed_queue,
    requeue_failed_jobs,
)
from app.core.request_context import request_id_var
from app.worker import (
    UnknownJobTypeError,
    handle_job,
    maybe_run_queue_maintenance,
    maybe_run_scheduled_maintenance,
    process_next_job,
    run_scheduled_maintenance,
)
from tests.test_job_queue import FakeRedis


def test_enqueue_job_propagates_request_id_from_context():
    redis = FakeRedis()
    request_id_token = request_id_var.set("request-123")

    try:
        enqueued_job = enqueue_job(
            "send_password_reset_email",
            {"user_id": 123},
            redis=redis,
            queue_name="test_jobs",
        )
    finally:
        request_id_var.reset(request_id_token)

    assert enqueued_job.request_id == "request-123"


def test_enqueue_and_dequeue_job_round_trip():
    redis = FakeRedis()

    enqueued_job = enqueue_job(
        "send_password_reset_email",
        {"user_id": 123},
        redis=redis,
        queue_name="test_jobs",
    )
    dequeued_job = dequeue_job(
        redis=redis,
        queue_name="test_jobs",
        processing_queue_name="test_processing",
        timeout_seconds=1,
    )

    assert dequeued_job == enqueued_job.with_processing_started_at(
        started_at=dequeued_job.processing_started_at,
    )
    assert dequeued_job.processing_started_at is not None


def test_dequeue_job_returns_none_when_queue_is_empty():
    redis = FakeRedis()

    dequeued_job = dequeue_job(
        redis=redis,
        queue_name="test_jobs",
        processing_queue_name="test_processing",
        timeout_seconds=1,
    )

    assert dequeued_job is None


def test_list_failed_jobs_returns_failed_queue_items():
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 123},
        attempts=3,
        last_error="boom",
        failed_at="2026-01-01T00:00:00+00:00",
    )

    move_job_to_failed_queue(
        job,
        redis=redis,
        processing_queue_name="test_processing",
        failed_queue_name="test_failed_jobs",
    )

    failed_jobs = list_failed_jobs(
        redis=redis,
        failed_queue_name="test_failed_jobs",
    )

    assert failed_jobs[0].id == job.id
    assert failed_jobs[0].last_error == "boom"
    assert failed_jobs[0].failed_at is not None


def test_requeue_failed_jobs_moves_jobs_back_to_main_queue():
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 123},
        attempts=3,
    )

    move_job_to_failed_queue(
        job,
        redis=redis,
        processing_queue_name="test_processing",
        failed_queue_name="test_failed_jobs",
    )

    requeued_count = requeue_failed_jobs(
        redis=redis,
        queue_name="test_jobs",
        failed_queue_name="test_failed_jobs",
    )

    dequeued_job = dequeue_job(
        redis=redis,
        queue_name="test_jobs",
        processing_queue_name="test_processing",
        timeout_seconds=1,
    )

    assert requeued_count == 1
    assert dequeued_job is not None
    assert dequeued_job.id == job.id
    assert dequeued_job.payload == job.payload


def test_handle_job_raises_for_unknown_job_type():
    job = Job(
        id="job-id",
        type="unknown_job_type",
        payload={"foo": "bar"},
        attempts=0,
    )

    try:
        handle_job(job)
    except UnknownJobTypeError as exc:
        assert exc.job_type == "unknown_job_type"
    else:
        raise AssertionError("expected UnknownJobTypeError")


def test_process_next_job_moves_unknown_job_type_to_failed_queue(monkeypatch):
    job = Job(
        id="job-id",
        type="unknown_job_type",
        payload={"foo": "bar"},
        attempts=0,
    )
    acked_jobs = []
    failed_jobs = []
    retried_jobs = []

    monkeypatch.setattr("app.worker.reclaim_stale_processing_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.promote_delayed_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.dequeue_job", lambda: job)
    monkeypatch.setattr(
        "app.worker.schedule_retry",
        lambda failed_job, error: retried_jobs.append(failed_job),
    )
    monkeypatch.setattr(
        "app.worker.move_job_to_failed_queue",
        lambda failed_job, error=None: failed_jobs.append(failed_job) or failed_job,
    )
    monkeypatch.setattr(
        "app.worker.ack_job",
        lambda queued_job: acked_jobs.append(queued_job),
    )

    processed = process_next_job()

    assert processed is True
    assert failed_jobs == [job]
    assert retried_jobs == []
    assert acked_jobs == []


def test_process_next_job_schedules_retry_with_backoff(monkeypatch):
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 1},
        attempts=0,
    )
    retried_jobs = []
    failed_jobs = []

    monkeypatch.setattr("app.worker.promote_delayed_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.dequeue_job", lambda: job)
    monkeypatch.setattr(
        "app.worker.handle_job",
        lambda queued_job: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        "app.worker.schedule_retry",
        lambda failed_job, error: retried_jobs.append(failed_job)
        or Job(
            id=failed_job.id,
            type=failed_job.type,
            payload=failed_job.payload,
            attempts=1,
            last_error=str(error),
        ),
    )
    monkeypatch.setattr(
        "app.worker.move_job_to_failed_queue",
        lambda failed_job, error=None: failed_jobs.append(failed_job),
    )

    processed = process_next_job()

    assert processed is True
    assert retried_jobs == [job]
    assert failed_jobs == []


def test_process_next_job_moves_job_to_failed_queue_after_max_retries(monkeypatch):
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 1},
        attempts=3,
    )
    retried_jobs = []
    failed_jobs = []

    monkeypatch.setattr("app.worker.promote_delayed_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.dequeue_job", lambda: job)
    monkeypatch.setattr(
        "app.worker.handle_job",
        lambda queued_job: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        "app.worker.schedule_retry",
        lambda failed_job, error: retried_jobs.append(failed_job),
    )
    monkeypatch.setattr(
        "app.worker.move_job_to_failed_queue",
        lambda failed_job, error=None: failed_jobs.append(failed_job) or failed_job,
    )

    processed = process_next_job()

    assert processed is True
    assert retried_jobs == []
    assert failed_jobs == [job]


def test_process_next_job_acknowledges_successful_jobs(monkeypatch):
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 1},
        attempts=0,
    )
    acked_jobs = []

    monkeypatch.setattr("app.worker.promote_delayed_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.dequeue_job", lambda: job)
    monkeypatch.setattr("app.worker.handle_job", lambda queued_job: None)
    monkeypatch.setattr(
        "app.worker.ack_job",
        lambda queued_job: acked_jobs.append(queued_job),
    )

    processed = process_next_job()

    assert processed is True
    assert acked_jobs == [job]


def test_process_next_job_returns_false_without_job(monkeypatch):
    monkeypatch.setattr("app.worker.promote_delayed_jobs", lambda: 0)
    monkeypatch.setattr("app.worker.dequeue_job", lambda: None)

    processed = process_next_job()

    assert processed is False


def test_scheduled_maintenance_runs_when_lock_acquired(monkeypatch):
    cleanup_calls = {
        "password_reset": 0, "idempotency": 0, "webhook_events": 0,
        "audit_logs": 0, "voice_sessions": 0, "reminders": 0,
    }

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setattr("app.worker.settings.worker_maintenance_enabled", True)
    monkeypatch.setattr("app.worker.try_acquire_maintenance_lock", lambda **kwargs: True)
    monkeypatch.setattr("app.worker.SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(
        "app.worker.cleanup_expired_password_reset_tokens",
        lambda db: cleanup_calls.__setitem__("password_reset", cleanup_calls["password_reset"] + 1) or 2,
    )
    monkeypatch.setattr(
        "app.worker.cleanup_expired_idempotency_records",
        lambda db: cleanup_calls.__setitem__("idempotency", cleanup_calls["idempotency"] + 1) or 3,
    )
    monkeypatch.setattr(
        "app.worker.cleanup_old_webhook_events",
        lambda db: cleanup_calls.__setitem__("webhook_events", cleanup_calls["webhook_events"] + 1) or 4,
    )
    monkeypatch.setattr(
        "app.worker.cleanup_old_audit_logs",
        lambda db: cleanup_calls.__setitem__("audit_logs", cleanup_calls["audit_logs"] + 1) or 5,
    )
    monkeypatch.setattr(
        "app.worker.expire_stale_sessions",
        lambda db: cleanup_calls.__setitem__("voice_sessions", cleanup_calls["voice_sessions"] + 1) or 0,
    )
    monkeypatch.setattr(
        "app.worker.enqueue_due_reminders",
        lambda db: cleanup_calls.__setitem__("reminders", cleanup_calls["reminders"] + 1) or 0,
    )

    did_run = run_scheduled_maintenance()

    assert did_run is True
    assert cleanup_calls == {
        "password_reset": 1,
        "idempotency": 1,
        "webhook_events": 1,
        "audit_logs": 1,
        "voice_sessions": 1,
        "reminders": 1,
    }


def test_scheduled_maintenance_skips_when_lock_not_acquired(monkeypatch):
    cleanup_calls = []

    monkeypatch.setattr("app.worker.settings.worker_maintenance_enabled", True)
    monkeypatch.setattr(
        "app.worker.try_acquire_maintenance_lock",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "app.worker.cleanup_expired_password_reset_tokens",
        lambda db: cleanup_calls.append(db),
    )

    did_run = run_scheduled_maintenance()

    assert did_run is False
    assert cleanup_calls == []


def test_scheduled_maintenance_can_be_disabled(monkeypatch):
    cleanup_calls = []

    monkeypatch.setattr("app.worker.settings.worker_maintenance_enabled", False)
    monkeypatch.setattr(
        "app.worker.cleanup_expired_password_reset_tokens",
        lambda db: cleanup_calls.append(db),
    )

    did_run = run_scheduled_maintenance()

    assert did_run is False
    assert cleanup_calls == []


def test_run_worker_stops_after_shutdown_request(monkeypatch):
    from app.core.shutdown import request_worker_shutdown, _worker_shutdown_requested
    from app.worker import run_worker

    _worker_shutdown_requested.clear()

    loop_iterations = {"count": 0}

    def fake_process_next_job():
        loop_iterations["count"] += 1
        request_worker_shutdown()
        return False

    monkeypatch.setattr("app.worker.maybe_run_scheduled_maintenance", lambda: False)
    monkeypatch.setattr("app.worker.maybe_run_queue_maintenance", lambda: None)
    monkeypatch.setattr("app.worker.process_next_job", fake_process_next_job)
    monkeypatch.setattr("app.worker.register_worker_shutdown_handlers", lambda: None)
    monkeypatch.setattr("app.worker.wait_for_worker_job_completion", lambda seconds: None)

    run_worker()

    assert loop_iterations["count"] == 1


def test_maybe_run_scheduled_maintenance_respects_interval(monkeypatch):
    monkeypatch.setattr("app.worker.settings.worker_maintenance_interval_seconds", 60)
    monkeypatch.setattr("app.worker._last_maintenance_attempt_at", 100.0)
    monkeypatch.setattr(
        "app.worker.run_scheduled_maintenance",
        lambda: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    did_run = maybe_run_scheduled_maintenance(now=120.0)

    assert did_run is False


def test_maybe_run_queue_maintenance_batches_promotion(monkeypatch):
    from app.core.config import settings

    calls = {"count": 0}

    monkeypatch.setattr("app.worker.settings.worker_queue_maintenance_interval_seconds", 5)
    monkeypatch.setattr("app.worker._last_queue_maintenance_at", 0.0)
    monkeypatch.setattr(
        "app.worker.reclaim_stale_processing_jobs",
        lambda: calls.__setitem__("reclaim", calls.get("reclaim", 0) + 1),
    )

    def fake_promote(**kwargs):
        calls["count"] += 1
        assert kwargs["limit"] == settings.worker_queue_promote_batch_size
        return 0

    monkeypatch.setattr("app.worker.promote_delayed_jobs", fake_promote)

    maybe_run_queue_maintenance(now=10.0)

    assert calls["count"] == 1
    assert calls["reclaim"] == 1
