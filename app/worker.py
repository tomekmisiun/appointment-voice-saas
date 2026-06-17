import logging
import time

from app.core.config import settings
from app.core.job_queue import (
    Job,
    ack_job,
    calculate_retry_delay_seconds,
    dequeue_job,
    move_job_to_failed_queue,
    promote_delayed_jobs,
    queue_name_for_job_type,
    reclaim_stale_processing_jobs,
    schedule_retry,
    try_acquire_maintenance_lock,
)
from app.core.log_helpers import job_log_extra
from app.core.logging import configure_logging
from app.core.metrics import configure_metrics, observe_worker_job, observe_worker_maintenance
from app.core.metrics_server import start_metrics_server
from app.core.shutdown import (
    mark_worker_job_finished,
    mark_worker_job_started,
    register_worker_shutdown_handlers,
    wait_for_worker_job_completion,
    worker_shutdown_requested,
)
from app.db.session import SessionLocal
from app.services.audit_log_service import cleanup_old_audit_logs
from app.services.idempotency_service import cleanup_expired_idempotency_records
from app.services.calendar_service import (
    CANCEL_CALENDAR_EVENT_JOB,
    SYNC_CALENDAR_EVENT_JOB,
    cancel_calendar_event_in_worker,
    sync_calendar_event_in_worker,
)
from app.services.notification_service import (
    SEND_NOTIFICATION_JOB,
    enqueue_due_reminders,
    send_notification_in_worker,
)
from app.services.password_reset_service import (
    SEND_PASSWORD_RESET_EMAIL_JOB,
    cleanup_expired_password_reset_tokens,
    create_password_reset_token_and_send_email,
)
from app.services.upload_verification_service import (
    VERIFY_PRESIGNED_UPLOAD_JOB,
    verify_presigned_upload_in_worker,
)
from app.services.ivr_service import expire_stale_sessions
from app.services.webhook_service import cleanup_old_webhook_events


logger = logging.getLogger("app.worker")

_last_maintenance_attempt_at = 0.0
_last_queue_maintenance_at = 0.0

# Each job type has its own queue (see queue_name_for_job_type()) so a stuck
# integration can't head-of-line block unrelated job types. The worker polls
# them in this fixed order, one short-timeout check per type per tick, so a
# job sitting in any one queue is found within roughly worker_poll_timeout_seconds
# regardless of how many types are registered.
_KNOWN_JOB_TYPES = (
    SEND_PASSWORD_RESET_EMAIL_JOB,
    SEND_NOTIFICATION_JOB,
    VERIFY_PRESIGNED_UPLOAD_JOB,
    SYNC_CALENDAR_EVENT_JOB,
    CANCEL_CALENDAR_EVENT_JOB,
)
_PER_QUEUE_POLL_TIMEOUT_SECONDS = max(
    1, settings.worker_poll_timeout_seconds // len(_KNOWN_JOB_TYPES)
)


class UnknownJobTypeError(Exception):
    def __init__(self, job_type: str):
        self.job_type = job_type
        super().__init__(f"unknown job type: {job_type}")


def handle_job(job: Job) -> None:
    if job.type == SEND_PASSWORD_RESET_EMAIL_JOB:
        user_id = job.payload["user_id"]

        db = SessionLocal()
        try:
            create_password_reset_token_and_send_email(
                db,
                user_id,
                job_id=job.id,
            )
        finally:
            db.close()

        return

    if job.type == SEND_NOTIFICATION_JOB:
        notification_id = job.payload["notification_id"]

        db = SessionLocal()
        try:
            send_notification_in_worker(db, notification_id=notification_id)
        finally:
            db.close()

        return

    if job.type == VERIFY_PRESIGNED_UPLOAD_JOB:
        uploaded_file_id = job.payload["uploaded_file_id"]

        db = SessionLocal()
        try:
            verify_presigned_upload_in_worker(
                db,
                uploaded_file_id=uploaded_file_id,
            )
        finally:
            db.close()

        return

    if job.type == SYNC_CALENDAR_EVENT_JOB:
        event_id = job.payload["event_id"]

        db = SessionLocal()
        try:
            sync_calendar_event_in_worker(db, event_id=event_id)
        finally:
            db.close()

        return

    if job.type == CANCEL_CALENDAR_EVENT_JOB:
        event_id = job.payload["event_id"]

        db = SessionLocal()
        try:
            cancel_calendar_event_in_worker(db, event_id=event_id)
        finally:
            db.close()

        return

    raise UnknownJobTypeError(job.type)


def process_next_job() -> bool:
    job = None
    for job_type in _KNOWN_JOB_TYPES:
        job = dequeue_job(
            queue_name=queue_name_for_job_type(job_type),
            timeout_seconds=_PER_QUEUE_POLL_TIMEOUT_SECONDS,
        )
        if job is not None:
            break

    if job is None:
        return False

    logger.info(
        "worker_job_started",
        extra={**job_log_extra(job), "attempts": job.attempts},
    )

    mark_worker_job_started()

    try:
        handle_job(job)
    except UnknownJobTypeError as exc:
        failed_job = move_job_to_failed_queue(job, exc)
        observe_worker_job(job_type=job.type, status="failed")
        logger.error(
            "worker_unknown_job_type",
            extra={**job_log_extra(failed_job), "attempts": failed_job.attempts},
        )
        return True
    except Exception as exc:
        if job.attempts < settings.worker_max_retries:
            retried_job = schedule_retry(job, exc)
            observe_worker_job(job_type=job.type, status="retry_scheduled")
            logger.exception(
                "worker_job_scheduled_for_retry",
                extra={
                    **job_log_extra(retried_job),
                    "attempts": retried_job.attempts,
                    "retry_delay_seconds": calculate_retry_delay_seconds(
                        retried_job.attempts
                    ),
                },
            )
            return True

        failed_job = move_job_to_failed_queue(job, exc)
        observe_worker_job(job_type=job.type, status="failed")
        logger.exception(
            "worker_job_failed",
            extra={**job_log_extra(failed_job), "attempts": failed_job.attempts},
        )
        return True
    finally:
        mark_worker_job_finished()

    ack_job(job)
    observe_worker_job(job_type=job.type, status="completed")
    logger.info("worker_job_completed", extra=job_log_extra(job))
    return True


def run_scheduled_maintenance(now: float | None = None) -> bool:
    del now

    if not settings.worker_maintenance_enabled:
        return False

    if not try_acquire_maintenance_lock(
        ttl_seconds=settings.worker_maintenance_interval_seconds,
    ):
        observe_worker_maintenance(status="skipped")
        return False

    db = SessionLocal()

    try:
        password_reset_deleted = cleanup_expired_password_reset_tokens(db)
        idempotency_deleted = cleanup_expired_idempotency_records(db)
        webhook_events_deleted = cleanup_old_webhook_events(db)
        audit_logs_deleted = cleanup_old_audit_logs(db)
        voice_sessions_expired = expire_stale_sessions(db)
        reminders_enqueued = enqueue_due_reminders(db)
    finally:
        db.close()

    logger.info(
        "worker_maintenance_completed "
        "expired_password_reset_tokens_deleted=%s "
        "expired_idempotency_records_deleted=%s "
        "old_webhook_events_deleted=%s "
        "old_audit_logs_deleted=%s "
        "voice_sessions_expired=%s "
        "reminders_enqueued=%s",
        password_reset_deleted,
        idempotency_deleted,
        webhook_events_deleted,
        audit_logs_deleted,
        voice_sessions_expired,
        reminders_enqueued,
    )
    observe_worker_maintenance(status="completed")

    return True


def maybe_run_scheduled_maintenance(now: float | None = None) -> bool:
    global _last_maintenance_attempt_at

    current_time = now if now is not None else time.monotonic()

    if (
        current_time - _last_maintenance_attempt_at
        < settings.worker_maintenance_interval_seconds
    ):
        return False

    _last_maintenance_attempt_at = current_time
    return run_scheduled_maintenance()


def maybe_run_queue_maintenance(now: float | None = None) -> None:
    global _last_queue_maintenance_at

    current_time = now if now is not None else time.monotonic()

    if (
        current_time - _last_queue_maintenance_at
        < settings.worker_queue_maintenance_interval_seconds
    ):
        return

    _last_queue_maintenance_at = current_time
    reclaim_stale_processing_jobs()
    promote_delayed_jobs(limit=settings.worker_queue_promote_batch_size)


def run_worker() -> None:
    configure_logging()
    configure_metrics()
    register_worker_shutdown_handlers()

    if settings.worker_metrics_enabled:
        start_metrics_server(
            host=settings.worker_metrics_host,
            port=settings.worker_metrics_port,
        )
        logger.info(
            "worker_metrics_server_started host=%s port=%s",
            settings.worker_metrics_host,
            settings.worker_metrics_port,
        )

    logger.info(
        "worker_started queues=%s",
        ",".join(queue_name_for_job_type(jt) for jt in _KNOWN_JOB_TYPES),
    )

    while not worker_shutdown_requested():
        maybe_run_scheduled_maintenance()

        if worker_shutdown_requested():
            break

        maybe_run_queue_maintenance()
        process_next_job()

    wait_for_worker_job_completion(settings.worker_shutdown_grace_seconds)
    logger.info("worker_shutdown_complete")


if __name__ == "__main__":
    run_worker()
