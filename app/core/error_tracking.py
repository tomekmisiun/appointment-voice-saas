import logging

import sentry_sdk

from app.core.config import Settings, settings
from app.core.request_context import get_request_id


logger = logging.getLogger("app.error_tracking")


def _attach_request_id_to_event(event, hint):
    del hint
    request_id = get_request_id()

    if request_id is None:
        return event

    tags = event.setdefault("tags", {})
    tags["request_id"] = request_id
    event.setdefault("contexts", {}).setdefault("request", {})[
        "request_id"
    ] = request_id

    return event


def initialize_error_tracking(app_settings: Settings = settings) -> bool:
    if not app_settings.sentry_dsn:
        logger.info("sentry_disabled")
        return False

    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        environment=app_settings.environment,
        traces_sample_rate=app_settings.sentry_traces_sample_rate,
        send_default_pii=app_settings.sentry_send_default_pii,
        release=app_settings.sentry_release or None,
        before_send=_attach_request_id_to_event,
    )
    logger.info("sentry_initialized environment=%s", app_settings.environment)

    return True
