from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.job_queue import (
    Job,
    ack_job,
    calculate_retry_delay_seconds,
    dequeue_job,
    enqueue_job,
    move_job_to_failed_queue,
    promote_delayed_jobs,
    queue_name_for_job_type,
    reclaim_stale_processing_jobs,
    schedule_retry,
    try_acquire_maintenance_lock,
)


class FakeRedis:
    def __init__(self):
        self.queues: dict[str, list[str]] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}
        self.strings: dict[str, str] = {}

    def lpush(self, queue_name: str, value: str) -> None:
        self.queues.setdefault(queue_name, []).insert(0, value)

    def brpop(self, queue_name: str, timeout: int):
        queue = self.queues.get(queue_name, [])

        if not queue:
            return None

        return queue_name, queue.pop()

    def brpoplpush(self, source_queue: str, destination_queue: str, timeout: int):
        queue = self.queues.get(source_queue, [])

        if not queue:
            return None

        value = queue.pop()
        self.queues.setdefault(destination_queue, []).insert(0, value)
        return value

    def lrem(self, queue_name: str, count: int, value: str) -> int:
        queue = self.queues.get(queue_name, [])
        removed = 0

        while value in queue and (count == 0 or removed < abs(count)):
            queue.remove(value)
            removed += 1

        return removed

    def lrange(self, queue_name: str, start: int, end: int):
        queue = self.queues.get(queue_name, [])
        stop = end + 1 if end >= 0 else None

        return queue[start:stop]

    def rpop(self, queue_name: str):
        queue = self.queues.get(queue_name, [])

        if not queue:
            return None

        return queue.pop()

    def zadd(self, queue_name: str, mapping: dict[str, float]) -> None:
        sorted_set = self.sorted_sets.setdefault(queue_name, {})
        sorted_set.update(mapping)

    def zrangebyscore(self, queue_name: str, min_score: float, max_score: float):
        sorted_set = self.sorted_sets.get(queue_name, {})

        return [
            member
            for member, score in sorted_set.items()
            if min_score <= score <= max_score
        ]

    def zrem(self, queue_name: str, member: str) -> int:
        sorted_set = self.sorted_sets.get(queue_name, {})

        if member not in sorted_set:
            return 0

        del sorted_set[member]
        return 1

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        del ex

        if nx and key in self.strings:
            return None

        self.strings[key] = value
        return True


def test_queue_name_for_job_type_namespaces_by_type():
    assert queue_name_for_job_type("send_notification", base_queue_name="app_jobs") == (
        "app_jobs:send_notification"
    )


def test_enqueue_job_defaults_to_per_type_queue():
    redis = FakeRedis()

    enqueued_job = enqueue_job("send_notification", {"x": 1}, redis=redis)

    queue_name = queue_name_for_job_type("send_notification")
    assert redis.queues[queue_name] == [enqueued_job.to_json()]


def test_enqueue_job_different_types_use_different_queues():
    redis = FakeRedis()

    enqueue_job("send_notification", {"x": 1}, redis=redis)
    enqueue_job("sync_calendar_event", {"y": 2}, redis=redis)

    assert len(redis.queues[queue_name_for_job_type("send_notification")]) == 1
    assert len(redis.queues[queue_name_for_job_type("sync_calendar_event")]) == 1


def test_calculate_retry_delay_seconds_uses_exponential_backoff():
    assert calculate_retry_delay_seconds(1) == settings.worker_retry_backoff_base_seconds
    assert calculate_retry_delay_seconds(2) == settings.worker_retry_backoff_base_seconds * 2
    assert (
        calculate_retry_delay_seconds(10)
        == settings.worker_retry_backoff_max_seconds
    )


def test_dequeue_moves_job_into_processing_queue():
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
    assert redis.queues["test_jobs"] == []
    assert redis.queues["test_processing"] == [dequeued_job.to_json()]


def test_ack_job_removes_job_from_processing_queue():
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="demo",
        payload={"value": 1},
        processing_started_at="2026-01-01T00:00:00+00:00",
    )
    redis.lpush("test_processing", job.to_json())

    ack_job(job, redis=redis, processing_queue_name="test_processing")

    assert redis.queues["test_processing"] == []


def test_schedule_retry_moves_job_to_delayed_queue_with_backoff():
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="demo",
        payload={"value": 1},
        attempts=0,
        processing_started_at="2026-01-01T00:00:00+00:00",
    )
    redis.lpush("test_processing", job.to_json())

    retried_job = schedule_retry(
        job,
        "temporary failure",
        redis=redis,
        processing_queue_name="test_processing",
        delayed_queue_name="test_delayed",
        now=100.0,
    )

    assert retried_job.attempts == 1
    assert retried_job.last_error == "temporary failure"
    assert redis.queues["test_processing"] == []
    assert retried_job.to_json() in redis.sorted_sets["test_delayed"]
    assert (
        redis.sorted_sets["test_delayed"][retried_job.to_json()]
        == 100.0 + settings.worker_retry_backoff_base_seconds
    )


def test_promote_delayed_jobs_moves_due_jobs_back_to_main_queue():
    redis = FakeRedis()
    job = Job(id="job-id", type="demo", payload={"value": 1}, attempts=1)
    redis.zadd("test_delayed", {job.to_json(): 50.0})

    promoted_count = promote_delayed_jobs(
        redis=redis,
        base_queue_name="test_jobs",
        delayed_queue_name="test_delayed",
        now=100.0,
    )

    queue_name = queue_name_for_job_type("demo", base_queue_name="test_jobs")
    assert promoted_count == 1
    assert redis.queues[queue_name] == [job.to_json()]
    assert redis.sorted_sets["test_delayed"] == {}


def test_promote_delayed_jobs_respects_batch_limit():
    redis = FakeRedis()
    first_job = Job(id="job-1", type="demo", payload={"value": 1}, attempts=1)
    second_job = Job(id="job-2", type="demo", payload={"value": 2}, attempts=1)
    redis.zadd(
        "test_delayed",
        {
            first_job.to_json(): 50.0,
            second_job.to_json(): 50.0,
        },
    )

    promoted_count = promote_delayed_jobs(
        redis=redis,
        base_queue_name="test_jobs",
        delayed_queue_name="test_delayed",
        now=100.0,
        limit=1,
    )

    queue_name = queue_name_for_job_type("demo", base_queue_name="test_jobs")
    assert promoted_count == 1
    assert len(redis.queues[queue_name]) == 1
    assert len(redis.sorted_sets["test_delayed"]) == 1


def test_move_job_to_failed_queue_persists_dead_letter_metadata():
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="demo",
        payload={"value": 1},
        attempts=3,
        processing_started_at="2026-01-01T00:00:00+00:00",
    )
    redis.lpush("test_processing", job.to_json())

    failed_job = move_job_to_failed_queue(
        job,
        "permanent failure",
        redis=redis,
        processing_queue_name="test_processing",
        failed_queue_name="test_failed",
    )

    assert failed_job.last_error == "permanent failure"
    assert failed_job.failed_at is not None
    assert redis.queues["test_processing"] == []
    assert redis.queues["test_failed"] == [failed_job.to_json()]


def test_try_acquire_maintenance_lock_is_exclusive():
    redis = FakeRedis()

    assert try_acquire_maintenance_lock(redis=redis, lock_key="maintenance") is True
    assert try_acquire_maintenance_lock(redis=redis, lock_key="maintenance") is False


def test_reclaim_stale_processing_jobs_returns_job_to_main_queue():
    redis = FakeRedis()
    stale_started_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=settings.worker_processing_visibility_timeout_seconds + 1)
    ).isoformat()
    stale_job = Job(
        id="job-id",
        type="demo",
        payload={"value": 1},
        processing_started_at=stale_started_at,
    )
    redis.lpush("test_processing", stale_job.to_json())

    reclaimed_count = reclaim_stale_processing_jobs(
        redis=redis,
        base_queue_name="test_jobs",
        processing_queue_name="test_processing",
        now=datetime.now(timezone.utc),
    )

    queue_name = queue_name_for_job_type("demo", base_queue_name="test_jobs")
    assert reclaimed_count == 1
    assert redis.queues["test_processing"] == []
    assert redis.queues[queue_name] == [stale_job.without_processing_started_at().to_json()]


def test_reclaim_stale_processing_jobs_reclaims_jobs_without_timestamp():
    redis = FakeRedis()
    legacy_job = Job(id="job-id", type="demo", payload={"value": 1})
    redis.lpush("test_processing", legacy_job.to_json())

    reclaimed_count = reclaim_stale_processing_jobs(
        redis=redis,
        base_queue_name="test_jobs",
        processing_queue_name="test_processing",
    )

    queue_name = queue_name_for_job_type("demo", base_queue_name="test_jobs")
    assert reclaimed_count == 1
    assert redis.queues["test_processing"] == []
    assert redis.queues[queue_name] == [legacy_job.to_json()]


def test_reclaim_stale_processing_jobs_skips_fresh_jobs():
    redis = FakeRedis()
    fresh_job = Job(
        id="job-id",
        type="demo",
        payload={"value": 1},
        processing_started_at=datetime.now(timezone.utc).isoformat(),
    )
    redis.lpush("test_processing", fresh_job.to_json())

    reclaimed_count = reclaim_stale_processing_jobs(
        redis=redis,
        base_queue_name="test_jobs",
        processing_queue_name="test_processing",
    )

    queue_name = queue_name_for_job_type("demo", base_queue_name="test_jobs")
    assert reclaimed_count == 0
    assert redis.queues["test_processing"] == [fresh_job.to_json()]
    assert redis.queues.get(queue_name, []) == []
