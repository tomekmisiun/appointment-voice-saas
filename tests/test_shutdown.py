import asyncio

from app.core.shutdown import (
    _worker_shutdown_requested,
    decrement_in_flight_requests,
    get_in_flight_request_count,
    increment_in_flight_requests,
    mark_worker_job_finished,
    mark_worker_job_started,
    request_worker_shutdown,
    wait_for_in_flight_requests,
    wait_for_worker_job_completion,
    worker_shutdown_requested,
)


def test_in_flight_request_tracking():
    assert get_in_flight_request_count() == 0

    increment_in_flight_requests()
    increment_in_flight_requests()

    assert get_in_flight_request_count() == 2

    decrement_in_flight_requests()

    assert get_in_flight_request_count() == 1

    decrement_in_flight_requests()

    assert get_in_flight_request_count() == 0


def test_wait_for_in_flight_requests_drains_active_requests():
    increment_in_flight_requests()

    async def drain_after_delay():
        await asyncio.sleep(0.05)
        decrement_in_flight_requests()

    async def run_drain():
        drain_task = asyncio.create_task(drain_after_delay())
        await wait_for_in_flight_requests(1.0)
        await drain_task

    asyncio.run(run_drain())

    assert get_in_flight_request_count() == 0


def test_worker_shutdown_flag():
    _worker_shutdown_requested.clear()

    assert worker_shutdown_requested() is False

    request_worker_shutdown()

    assert worker_shutdown_requested() is True

    _worker_shutdown_requested.clear()


def test_wait_for_worker_job_completion_returns_when_job_finishes():
    mark_worker_job_started()

    async def finish_job():
        await asyncio.sleep(0.05)
        mark_worker_job_finished()

    async def run_wait():
        finish_task = asyncio.create_task(finish_job())
        await asyncio.to_thread(wait_for_worker_job_completion, 1.0)
        await finish_task

    asyncio.run(run_wait())
