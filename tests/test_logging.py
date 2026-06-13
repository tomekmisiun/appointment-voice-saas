import json
import logging

from app.core.logging import (
    JsonLogFormatter,
    REDACTED_VALUE,
    RequestLogFormatter,
    SensitiveDataFilter,
    build_log_payload,
    redact_sensitive_value,
)


def format_log_record(record: logging.LogRecord) -> str:
    formatter = RequestLogFormatter(
        "request_id=%(request_id)s method=%(method)s path=%(path)s "
        "status=%(status_code)s process_time=%(process_time)s "
        "job_id=%(job_id)s job_type=%(job_type)s "
        "message=%(message)s"
    )

    return formatter.format(record)


def test_request_log_formatter_includes_request_fields():
    record = logging.LogRecord(
        name="app.requests",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_finished",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-1"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.process_time = 0.123

    formatted_log = format_log_record(record)

    assert "request_id=request-1" in formatted_log
    assert "method=GET" in formatted_log
    assert "path=/health" in formatted_log
    assert "status=200" in formatted_log
    assert "process_time=0.123" in formatted_log
    assert "message=request_finished" in formatted_log


def test_request_log_formatter_handles_missing_request_fields():
    record = logging.LogRecord(
        name="app.other",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="regular_log",
        args=(),
        exc_info=None,
    )

    formatted_log = format_log_record(record)

    assert "request_id=-" in formatted_log
    assert "method=-" in formatted_log
    assert "path=-" in formatted_log
    assert "status=-" in formatted_log
    assert "process_time=-" in formatted_log
    assert "job_id=-" in formatted_log
    assert "job_type=-" in formatted_log
    assert "message=regular_log" in formatted_log


def test_json_log_formatter_emits_structured_payload():
    record = logging.LogRecord(
        name="app.worker",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="worker_job_started",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-1"
    record.job_id = "job-1"
    record.job_type = "send_password_reset_email"
    record.attempts = 0

    formatted_log = JsonLogFormatter().format(record)
    payload = json.loads(formatted_log)

    assert payload["message"] == "worker_job_started"
    assert payload["request_id"] == "request-1"
    assert payload["job_id"] == "job-1"
    assert payload["job_type"] == "send_password_reset_email"
    assert payload["attempts"] == 0
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.worker"


def test_redact_sensitive_value_masks_known_fields():
    assert redact_sensitive_value("password", "secret-value") == REDACTED_VALUE
    assert redact_sensitive_value("recipient", "user@example.com") == REDACTED_VALUE
    assert redact_sensitive_value("job_id", "job-1") == "job-1"


def test_sensitive_data_filter_redacts_extra_fields():
    record = logging.LogRecord(
        name="app.email",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="password_reset_email_sent",
        args=(),
        exc_info=None,
    )
    record.recipient = "user@example.com"

    SensitiveDataFilter().filter(record)

    assert record.recipient == REDACTED_VALUE


def test_build_log_payload_redacts_sensitive_extra_fields():
    record = logging.LogRecord(
        name="app.email",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="password_reset_email_sent",
        args=(),
        exc_info=None,
    )
    record.recipient = "user@example.com"
    record.job_id = "job-1"

    payload = build_log_payload(record)

    assert payload["recipient"] == REDACTED_VALUE
    assert payload["job_id"] == "job-1"
