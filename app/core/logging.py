import json
import logging
import re
from datetime import datetime, timezone

from app.core.config import settings


REQUEST_LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "process_time",
    "job_id",
    "job_type",
)

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "new_password",
        "old_password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "secret",
        "secret_key",
        "smtp_password",
        "s3_secret_access_key",
        "api_key",
        "email",
        "recipient",
    }
)

REDACTED_VALUE = "[REDACTED]"
EMAIL_PATTERN = re.compile(r"[^@]+@[^@]+\.[^@]+")

STANDARD_LOG_RECORD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def redact_sensitive_value(field_name: str, value: object) -> object:
    normalized_field_name = field_name.lower()

    if normalized_field_name in SENSITIVE_FIELD_NAMES:
        return REDACTED_VALUE

    if isinstance(value, str) and EMAIL_PATTERN.search(value):
        return REDACTED_VALUE

    return value


def build_log_payload(record: logging.LogRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }

    for field in REQUEST_LOG_FIELDS:
        value = getattr(record, field, None)
        payload[field] = redact_sensitive_value(field, value if value is not None else "-")

    for field_name, value in record.__dict__.items():
        if field_name in STANDARD_LOG_RECORD_FIELDS or field_name in REQUEST_LOG_FIELDS:
            continue

        payload[field_name] = redact_sensitive_value(field_name, value)

    return payload


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for field_name in list(record.__dict__):
            if field_name in STANDARD_LOG_RECORD_FIELDS:
                continue

            record.__dict__[field_name] = redact_sensitive_value(
                field_name,
                record.__dict__[field_name],
            )

        return True


class RequestLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        for field in REQUEST_LOG_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, "-")

        return super().format(record)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        for field in REQUEST_LOG_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, "-")

        return json.dumps(build_log_payload(record), default=str)


def configure_logging() -> None:
    if settings.log_format == "json":
        formatter: logging.Formatter = JsonLogFormatter()
    else:
        formatter = RequestLogFormatter(
            "%(asctime)s %(levelname)s %(name)s "
            "request_id=%(request_id)s method=%(method)s path=%(path)s "
            "status=%(status_code)s process_time=%(process_time)s "
            "job_id=%(job_id)s job_type=%(job_type)s "
            "message=%(message)s"
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    logging.getLogger("app.requests").setLevel(settings.log_level)
