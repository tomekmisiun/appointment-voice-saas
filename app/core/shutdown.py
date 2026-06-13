import asyncio
import logging
import signal
import threading
import time

logger = logging.getLogger("app.shutdown")

_in_flight_requests = 0
_in_flight_lock = threading.Lock()
_worker_shutdown_requested = threading.Event()
_worker_job_in_progress = threading.Event()


def increment_in_flight_requests() -> None:
    global _in_flight_requests

    with _in_flight_lock:
        _in_flight_requests += 1


def decrement_in_flight_requests() -> None:
    global _in_flight_requests

    with _in_flight_lock:
        _in_flight_requests -= 1


def get_in_flight_request_count() -> int:
    with _in_flight_lock:
        return _in_flight_requests


async def wait_for_in_flight_requests(grace_seconds: float) -> None:
    if grace_seconds <= 0:
        return

    deadline = time.monotonic() + grace_seconds

    while time.monotonic() < deadline:
        if get_in_flight_request_count() == 0:
            logger.info("api_shutdown_drain_complete in_flight=0")
            return

        await asyncio.sleep(0.1)

    logger.warning(
        "api_shutdown_drain_timeout in_flight=%s grace_seconds=%s",
        get_in_flight_request_count(),
        grace_seconds,
    )


def request_worker_shutdown(signum: int | None = None, _frame=None) -> None:
    _worker_shutdown_requested.set()
    logger.info("worker_shutdown_requested signal=%s", signum)


def worker_shutdown_requested() -> bool:
    return _worker_shutdown_requested.is_set()


def register_worker_shutdown_handlers() -> None:
    signal.signal(signal.SIGTERM, request_worker_shutdown)
    signal.signal(signal.SIGINT, request_worker_shutdown)


def mark_worker_job_started() -> None:
    _worker_job_in_progress.set()


def mark_worker_job_finished() -> None:
    _worker_job_in_progress.clear()


def wait_for_worker_job_completion(grace_seconds: float) -> None:
    if not _worker_job_in_progress.is_set():
        return

    deadline = time.monotonic() + grace_seconds

    while time.monotonic() < deadline:
        if not _worker_job_in_progress.is_set():
            logger.info("worker_shutdown_job_completed")
            return

        time.sleep(0.1)

    logger.warning(
        "worker_shutdown_job_timeout grace_seconds=%s",
        grace_seconds,
    )
