from app.core.request_context import get_request_id


def job_log_extra(job) -> dict[str, object]:
    extra: dict[str, object] = {
        "job_id": job.id,
        "job_type": job.type,
    }

    request_id = job.request_id or get_request_id()

    if request_id is not None:
        extra["request_id"] = request_id

    return extra
