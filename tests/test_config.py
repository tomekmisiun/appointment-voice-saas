import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings_kwargs():
    return {
        "environment": "production",
        "secret_key": "strong-production-secret-key-value",
        "database_url": "postgresql://prod_user:prod_password@postgres:5432/prod_db",
        "smtp_host": "smtp.example.test",
        "smtp_username": "smtp-user",
        "smtp_password": "smtp-password",
        "email_from": "noreply@app.example.test",
        "password_reset_url": "https://app.example.test/reset-password",
        "s3_endpoint_url": "https://s3.example.test",
        "s3_access_key_id": "prod-access-key",
        "s3_secret_access_key": "prod-secret-key",
        "s3_bucket_name": "prod-uploads",
        "redis_host": "redis.example.test",
        "redis_password": "redis-production-password",
        "trusted_hosts_enabled": True,
        "trusted_hosts": "api.example.test",
        "rate_limit_trust_forwarded_headers": True,
        "metrics_bearer_token": "metrics-bearer-token-with-32-characters-min",
        "webhook_signature_secret": "production-webhook-secret-with-32-characters",
        "upload_malware_scan_enabled": True,
        "upload_malware_scanner_url": "https://scanner.example.test/scan",
    }


def staging_settings_kwargs():
    return {
        **production_settings_kwargs(),
        "environment": "staging",
        "secret_key": "strong-staging-secret-key-value-here",
        "trusted_hosts_enabled": False,
        "trusted_hosts": "",
        "webhook_signature_secret": "",
    }


def test_settings_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_weak_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="change-me",
        )


def test_settings_rejects_unknown_environment():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="local",
            secret_key="development-secret",
        )


def test_settings_accepts_registration_policy_values():
    public_settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        registration_policy="public",
    )
    disabled_settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        registration_policy="disabled",
    )

    assert public_settings.registration_enabled is True
    assert disabled_settings.registration_enabled is False


def test_settings_rejects_unknown_registration_policy():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            registration_policy="invite_only",
        )


def test_settings_accepts_staging_environment():
    settings = Settings(
        _env_file=None,
        **staging_settings_kwargs(),
    )

    assert settings.environment == "staging"


def test_settings_rejects_local_staging_placeholders():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            environment="staging",
            secret_key="strong-staging-secret-key-value-here",
        )

    error_message = str(exc_info.value)
    assert "database_url must not use the local Docker default in staging" in error_message
    assert "redis_host must not use a local Docker or loopback host in staging" in error_message


def test_settings_accepts_staging_without_trusted_hosts_or_webhook_secret():
    settings = Settings(
        _env_file=None,
        **staging_settings_kwargs(),
    )

    assert settings.trusted_hosts_enabled is False
    assert settings.webhook_signature_secret == ""


def test_settings_rejects_short_staging_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                **staging_settings_kwargs(),
                "secret_key": "short-secret",
            },
        )


def test_settings_rejects_short_production_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                **production_settings_kwargs(),
                "secret_key": "short-secret",
            },
        )


def test_settings_rejects_local_production_placeholders():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-production-secret-key-value",
        )

    error_message = str(exc_info.value)

    assert "database_url must not use the local Docker default" in error_message
    assert "smtp_host is required in production" in error_message
    assert "smtp_username is required in production" in error_message
    assert "smtp_password is required in production" in error_message
    assert "email_from must not use the example placeholder" in error_message
    assert "password_reset_url must not use a localhost URL" in error_message
    assert "s3_endpoint_url must not use a local MinIO URL" in error_message
    assert "s3_access_key_id must not use the local MinIO default" in error_message
    assert "s3_secret_access_key must not use the local MinIO default" in error_message
    assert "s3_bucket_name must not use the local default" in error_message
    assert "redis_host must not use a local Docker or loopback host" in error_message
    assert "redis_password is required in production" in error_message
    assert "trusted_hosts_enabled must be true in production" in error_message
    assert "trusted_hosts is required in production" in error_message
    assert "webhook_signature_secret is required in production" in error_message


def test_settings_accepts_strong_production_secret_key():
    settings = Settings(
        _env_file=None,
        **production_settings_kwargs(),
    )

    assert settings.environment == "production"
    assert settings.secret_key == "strong-production-secret-key-value"
    assert settings.legacy_routes_enabled is False


def test_settings_rejects_production_without_malware_scanner_url():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            **{
                **production_settings_kwargs(),
                "upload_malware_scanner_url": "",
            },
        )

    error_message = str(exc_info.value)
    assert "upload_malware_scanner_url is required in production" in error_message


def test_settings_rejects_production_with_malware_scan_disabled():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            **{
                **production_settings_kwargs(),
                "upload_malware_scan_enabled": False,
            },
        )

    error_message = str(exc_info.value)
    assert "upload_malware_scan_enabled must be true in production" in error_message


def test_settings_default_legacy_routes_enabled_in_development():
    settings = Settings(
        _env_file=None,
        secret_key="strong-development-secret-key-value",
        environment="development",
    )

    assert settings.legacy_routes_enabled is True


def test_settings_allows_explicit_legacy_routes_in_production():
    settings = Settings(
        _env_file=None,
        **{
            **production_settings_kwargs(),
            "legacy_routes_enabled": True,
        },
    )

    assert settings.legacy_routes_enabled is True


def test_settings_rejects_weak_production_webhook_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            **{
                **production_settings_kwargs(),
                "webhook_signature_secret": "change-me",
            },
        )

    assert "webhook_signature_secret must not use a known weak placeholder" in str(
        exc_info.value
    )


def test_settings_accepts_rate_limit_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        rate_limit_default_limit=10,
        rate_limit_default_window_seconds=30,
    )

    assert settings.rate_limit_default_limit == 10
    assert settings.rate_limit_default_window_seconds == 30


def test_settings_accepts_jwt_ttl_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        access_token_expire_minutes=15,
        refresh_token_expire_days=14,
    )

    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 14


def test_settings_accepts_auth_refresh_and_logout_rate_limit_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        auth_refresh_rate_limit_limit=20,
        auth_refresh_rate_limit_window_seconds=120,
        auth_logout_rate_limit_limit=10,
        auth_logout_rate_limit_window_seconds=90,
    )

    assert settings.auth_refresh_rate_limit_limit == 20
    assert settings.auth_refresh_rate_limit_window_seconds == 120
    assert settings.auth_logout_rate_limit_limit == 10
    assert settings.auth_logout_rate_limit_window_seconds == 90


def test_settings_rejects_non_positive_rate_limit_config():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            rate_limit_default_limit=0,
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            rate_limit_default_window_seconds=0,
        )


def test_settings_accepts_sentry_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
        sentry_traces_sample_rate=0.5,
        sentry_send_default_pii=True,
        sentry_release="template@1.2.3",
    )

    assert settings.sentry_dsn == "https://public@example.ingest.sentry.io/1"
    assert settings.sentry_traces_sample_rate == 0.5
    assert settings.sentry_send_default_pii is True
    assert settings.sentry_release == "template@1.2.3"


def test_settings_rejects_invalid_sentry_traces_sample_rate():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            sentry_traces_sample_rate=-0.1,
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            sentry_traces_sample_rate=1.1,
        )


def test_settings_accepts_worker_maintenance_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        worker_maintenance_enabled=False,
        worker_maintenance_interval_seconds=120,
    )

    assert settings.worker_maintenance_enabled is False
    assert settings.worker_maintenance_interval_seconds == 120


def test_settings_rejects_invalid_worker_maintenance_interval():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            worker_maintenance_interval_seconds=0,
        )


def test_settings_accepts_worker_observability_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        worker_metrics_enabled=False,
        worker_metrics_port=9200,
        worker_queue_maintenance_interval_seconds=15,
        worker_queue_promote_batch_size=25,
    )

    assert settings.worker_metrics_enabled is False
    assert settings.worker_metrics_port == 9200
    assert settings.worker_queue_maintenance_interval_seconds == 15
    assert settings.worker_queue_promote_batch_size == 25


def test_settings_accepts_worker_retry_backoff_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        worker_retry_backoff_base_seconds=10,
        worker_retry_backoff_max_seconds=120,
        worker_processing_queue_name="jobs_processing",
        worker_delayed_queue_name="jobs_delayed",
    )

    assert settings.worker_retry_backoff_base_seconds == 10
    assert settings.worker_retry_backoff_max_seconds == 120
    assert settings.worker_processing_queue_name == "jobs_processing"
    assert settings.worker_delayed_queue_name == "jobs_delayed"


def test_settings_rejects_invalid_worker_retry_backoff_range():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            worker_retry_backoff_base_seconds=60,
            worker_retry_backoff_max_seconds=30,
        )


def test_settings_accepts_database_pool_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        db_pool_size=10,
        db_max_overflow=20,
        db_pool_recycle_seconds=900,
        db_pool_pre_ping=False,
        db_pool_timeout_seconds=15,
        db_statement_timeout_ms=5000,
    )

    assert settings.db_pool_size == 10
    assert settings.db_max_overflow == 20
    assert settings.db_pool_recycle_seconds == 900
    assert settings.db_pool_pre_ping is False
    assert settings.db_pool_timeout_seconds == 15
    assert settings.db_statement_timeout_ms == 5000


def test_settings_accepts_redis_connection_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        redis_username="redis-user",
        redis_password="redis-password",
        redis_ssl=True,
        redis_ssl_cert_reqs="optional",
        redis_socket_timeout_seconds=2.5,
        redis_socket_connect_timeout_seconds=1.5,
    )

    assert settings.redis_username == "redis-user"
    assert settings.redis_password == "redis-password"
    assert settings.redis_ssl is True
    assert settings.redis_ssl_cert_reqs == "optional"
    assert settings.redis_socket_timeout_seconds == 2.5
    assert settings.redis_socket_connect_timeout_seconds == 1.5


def test_settings_rejects_invalid_redis_ssl_cert_reqs():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="development-secret",
            redis_ssl_cert_reqs="invalid",
        )


def test_settings_accepts_runtime_security_config():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        cors_enabled=True,
        cors_allow_origins="https://app.example.test",
        cors_allow_credentials=True,
        trusted_hosts_enabled=True,
        trusted_hosts="api.example.test,localhost",
        security_headers_enabled=True,
        hsts_enabled=True,
        hsts_max_age_seconds=86400,
    )

    assert settings.cors_origins_list() == ["https://app.example.test"]
    assert settings.trusted_hosts_list() == ["api.example.test", "localhost"]
    assert settings.cors_methods_list() == [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ]
    assert settings.hsts_enabled is True


def test_settings_rejects_production_cors_wildcard():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                **production_settings_kwargs(),
                "cors_enabled": True,
                "cors_allow_origins": "*",
            },
        )
