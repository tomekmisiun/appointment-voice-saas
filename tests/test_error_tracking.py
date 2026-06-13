from tests.test_config import staging_settings_kwargs
from app.core.config import Settings
from app.core.error_tracking import initialize_error_tracking
from app.core.request_context import request_id_var


def test_initialize_error_tracking_is_disabled_without_dsn(monkeypatch):
    def fail_init(**kwargs):
        raise AssertionError("sentry_sdk.init should not be called without a DSN")

    monkeypatch.setattr("app.core.error_tracking.sentry_sdk.init", fail_init)

    initialized = initialize_error_tracking(
        Settings(
            _env_file=None,
            secret_key="development-secret",
        )
    )

    assert initialized is False


def test_initialize_error_tracking_calls_sentry_with_config(monkeypatch):
    init_calls = []

    def fake_init(**kwargs):
        init_calls.append(kwargs)

    monkeypatch.setattr("app.core.error_tracking.sentry_sdk.init", fake_init)

    initialized = initialize_error_tracking(
        Settings(
            _env_file=None,
            **staging_settings_kwargs(),
            sentry_dsn="https://public@example.ingest.sentry.io/1",
            sentry_traces_sample_rate=0.25,
            sentry_send_default_pii=True,
            sentry_release="template@1.2.3",
        )
    )

    assert initialized is True
    assert init_calls[0]["dsn"] == "https://public@example.ingest.sentry.io/1"
    assert init_calls[0]["environment"] == "staging"
    assert init_calls[0]["traces_sample_rate"] == 0.25
    assert init_calls[0]["send_default_pii"] is True
    assert init_calls[0]["release"] == "template@1.2.3"
    assert callable(init_calls[0]["before_send"])


def test_error_tracking_before_send_attaches_request_id(monkeypatch):
    init_calls = []

    def fake_init(**kwargs):
        init_calls.append(kwargs)

    monkeypatch.setattr("app.core.error_tracking.sentry_sdk.init", fake_init)

    initialize_error_tracking(
        Settings(
            _env_file=None,
            secret_key="development-secret",
            sentry_dsn="https://public@example.ingest.sentry.io/1",
        )
    )

    request_id_token = request_id_var.set("request-456")
    try:
        event = init_calls[0]["before_send"]({"tags": {}}, None)
    finally:
        request_id_var.reset(request_id_token)

    assert event["tags"]["request_id"] == "request-456"
    assert event["contexts"]["request"]["request_id"] == "request-456"
