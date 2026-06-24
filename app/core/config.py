import os
from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ALLOWED_ENVIRONMENTS = {"development", "test", "staging", "production"}
ALLOWED_LOG_FORMATS = {"text", "json"}
ALLOWED_REGISTRATION_POLICIES = {"public", "disabled"}
WEAK_SECRET_KEYS = {"change-me", "changeme", "secret", "test", "password"}
LOCAL_DATABASE_URL = "postgresql://app_user:app_password@db:5432/app_db"
LOCAL_PASSWORD_RESET_URLS = {
    "http://localhost:8000/reset-password",
    "http://127.0.0.1:8000/reset-password",
}
LOCAL_S3_ENDPOINT_URLS = {
    "http://minio:9000",
    "http://localhost:9000",
    "http://127.0.0.1:9000",
}
LOCAL_S3_CREDENTIALS = {"minioadmin"}
LOCAL_REDIS_HOST = "redis"
LOCAL_REDIS_HOSTS = {LOCAL_REDIS_HOST, "localhost", "127.0.0.1"}
ALLOWED_REDIS_SSL_CERT_REQS = {"none", "optional", "required"}
PLACEHOLDER_EMAILS = {"noreply@example.com"}


def parse_csv_setting(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    app_name: str = "Appointment Voice SaaS API"
    environment: str = "development"
    database_url: str = Field(default=LOCAL_DATABASE_URL)
    secret_key: str = Field(min_length=1)
    algorithm: str = "HS256"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str = ""
    redis_password: str = ""
    redis_ssl: bool = False
    redis_ssl_cert_reqs: str = "required"
    redis_socket_timeout_seconds: float = Field(default=5.0, gt=0)
    redis_socket_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    db_pool_size: int = Field(default=5, gt=0)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_recycle_seconds: int = Field(default=1800, gt=0)
    db_pool_pre_ping: bool = True
    db_pool_timeout_seconds: int = Field(default=30, gt=0)
    db_statement_timeout_ms: int = Field(default=0, ge=0)
    cors_enabled: bool = False
    cors_allow_origins: str = ""
    cors_allow_credentials: bool = False
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    trusted_hosts_enabled: bool = False
    trusted_hosts: str = ""
    security_headers_enabled: bool = True
    hsts_enabled: bool = False
    hsts_max_age_seconds: int = Field(default=31536000, gt=0)
    log_level: str = "INFO"
    log_format: str = "text"
    rate_limit_default_limit: int = Field(default=5, gt=0)
    rate_limit_default_window_seconds: int = Field(default=60, gt=0)
    password_reset_rate_limit_limit: int = Field(default=3, gt=0)
    password_reset_rate_limit_window_seconds: int = Field(default=300, gt=0)
    auth_login_rate_limit_limit: int = Field(default=10, gt=0)
    auth_login_rate_limit_window_seconds: int = Field(default=60, gt=0)
    auth_register_rate_limit_limit: int = Field(default=5, gt=0)
    auth_register_rate_limit_window_seconds: int = Field(default=300, gt=0)
    auth_refresh_rate_limit_limit: int = Field(default=30, gt=0)
    auth_refresh_rate_limit_window_seconds: int = Field(default=60, gt=0)
    auth_logout_rate_limit_limit: int = Field(default=30, gt=0)
    auth_logout_rate_limit_window_seconds: int = Field(default=60, gt=0)
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    rate_limit_trust_forwarded_headers: bool = False
    registration_policy: str = "public"
    legacy_routes_enabled: bool | None = None
    smtp_host: str = ""
    smtp_port: int = Field(default=587, gt=0)
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"
    password_reset_url: str = "http://localhost:8000/reset-password"
    password_reset_token_expire_minutes: int = Field(default=30, gt=0)
    password_reset_job_completion_ttl_seconds: int = Field(default=86400, gt=0)
    worker_queue_name: str = "app_jobs"
    worker_failed_queue_name: str = "app_jobs_failed"
    worker_processing_queue_name: str = "app_jobs_processing"
    worker_delayed_queue_name: str = "app_jobs_delayed"
    worker_poll_timeout_seconds: int = Field(default=5, gt=0)
    worker_max_retries: int = Field(default=3, ge=0)
    worker_retry_backoff_base_seconds: int = Field(default=5, gt=0)
    worker_retry_backoff_max_seconds: int = Field(default=300, gt=0)
    worker_processing_visibility_timeout_seconds: int = Field(default=300, gt=0)
    worker_maintenance_enabled: bool = True
    worker_maintenance_interval_seconds: int = Field(default=3600, gt=0)
    worker_maintenance_lock_key: str = "app_jobs_maintenance_lock"
    worker_maintenance_lock_ttl_seconds: int = Field(default=300, gt=0)
    worker_metrics_enabled: bool = True
    worker_metrics_host: str = "0.0.0.0"
    worker_metrics_port: int = Field(default=9100, gt=0)
    worker_queue_maintenance_interval_seconds: int = Field(default=5, gt=0)
    worker_queue_promote_batch_size: int = Field(default=100, gt=0)
    worker_reconciliation_stale_minutes: int = Field(default=15, gt=0)
    users_cache_enabled: bool = True
    users_cache_ttl_seconds: int = Field(default=60, gt=0)
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "uploads"
    s3_region_name: str = "us-east-1"
    upload_max_size_bytes: int = Field(default=5_242_880, gt=0)
    upload_allowed_content_types: str = "image/png,image/jpeg,application/pdf"
    upload_presigned_url_expire_seconds: int = Field(default=300, gt=0)
    upload_stream_chunk_size_bytes: int = Field(default=65_536, gt=0)
    upload_spool_max_memory_bytes: int = Field(default=1_048_576, gt=0)
    upload_malware_scan_enabled: bool = False
    upload_malware_scanner_url: str = ""
    upload_malware_scanner_timeout_seconds: float = Field(default=5.0, gt=0)
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    sentry_send_default_pii: bool = False
    sentry_release: str = ""
    prometheus_multiproc_dir: str = ""
    metrics_instance_id: str = ""
    metrics_require_auth: bool | None = None
    metrics_bearer_token: str = ""
    webhook_signature_secret: str = ""
    webhook_signature_tolerance_seconds: int = Field(default=300, gt=0)
    webhook_event_retention_days: int = Field(default=90, gt=0)
    audit_log_retention_days: int = Field(default=365, gt=0)
    webhook_max_body_bytes: int = Field(default=1_048_576, gt=0)
    webhook_ingress_rate_limit_limit: int = Field(default=60, gt=0)
    webhook_ingress_rate_limit_window_seconds: int = Field(default=60, gt=0)
    webhook_provider_rate_limit_limit: int = Field(default=120, gt=0)
    webhook_provider_rate_limit_window_seconds: int = Field(default=60, gt=0)
    idempotency_ttl_seconds: int = Field(default=86400, gt=0)
    idempotency_processing_lock_ttl_seconds: int = Field(default=60, gt=0)
    api_shutdown_grace_seconds: float = Field(default=30.0, ge=0)
    ivr_session_ttl_minutes: int = Field(default=10, gt=0)
    ivr_slot_search_days: int = Field(default=7, gt=0)
    ivr_max_slots: int = Field(default=5, gt=0)
    reminder_lead_minutes: int = Field(default=1440, gt=0)
    waitlist_offer_timeout_minutes: int = Field(default=60, gt=0)
    worker_shutdown_grace_seconds: float = Field(default=60.0, ge=0)
    readiness_check_s3_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_voice_base_url: str = ""
    twilio_voice_rate_limit_limit: int = Field(default=120, gt=0)
    twilio_voice_rate_limit_window_seconds: int = Field(default=60, gt=0)
    twilio_sms_status_rate_limit_limit: int = Field(default=300, gt=0)
    twilio_sms_status_rate_limit_window_seconds: int = Field(default=60, gt=0)
    twilio_sms_inbound_rate_limit_limit: int = Field(default=300, gt=0)
    twilio_sms_inbound_rate_limit_window_seconds: int = Field(default=60, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    test_database_url: str = Field(
        default="postgresql://app_user:app_password@test_db:5432/app_test_db"
    )

    @field_validator("prometheus_multiproc_dir", mode="before")
    @classmethod
    def normalize_prometheus_multiproc_dir(cls, value: object) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @model_validator(mode="after")
    def clear_empty_prometheus_multiproc_env(self) -> Self:
        if not self.prometheus_multiproc_dir:
            os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)

        return self

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized_environment = value.lower()

        if normalized_environment not in ALLOWED_ENVIRONMENTS:
            allowed_values = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
            raise ValueError(f"environment must be one of: {allowed_values}")

        return normalized_environment

    @field_validator("registration_policy")
    @classmethod
    def validate_registration_policy(cls, value: str) -> str:
        normalized_policy = value.lower()

        if normalized_policy not in ALLOWED_REGISTRATION_POLICIES:
            allowed_values = ", ".join(sorted(ALLOWED_REGISTRATION_POLICIES))
            raise ValueError(
                f"registration_policy must be one of: {allowed_values}",
            )

        return normalized_policy

    @property
    def registration_enabled(self) -> bool:
        return self.registration_policy == "public"

    def _collect_remote_environment_errors(
        self,
        *,
        environment_name: str,
        require_trusted_hosts: bool,
        require_webhook_secret: bool,
    ) -> list[str]:
        secret_key = self.secret_key.strip()
        errors: list[str] = []

        if len(secret_key) < 32:
            errors.append(
                f"secret_key must be at least 32 characters in {environment_name}",
            )

        if self.database_url == LOCAL_DATABASE_URL:
            errors.append(
                f"database_url must not use the local Docker default in {environment_name}",
            )

        if self.smtp_host.strip() == "":
            errors.append(f"smtp_host is required in {environment_name}")

        if self.smtp_username.strip() == "":
            errors.append(f"smtp_username is required in {environment_name}")

        if self.smtp_password.strip() == "":
            errors.append(f"smtp_password is required in {environment_name}")

        if self.email_from.lower() in PLACEHOLDER_EMAILS:
            errors.append(
                f"email_from must not use the example placeholder in {environment_name}",
            )

        if self.password_reset_url in LOCAL_PASSWORD_RESET_URLS:
            errors.append(
                f"password_reset_url must not use a localhost URL in {environment_name}",
            )

        if self.s3_endpoint_url in LOCAL_S3_ENDPOINT_URLS:
            errors.append(
                f"s3_endpoint_url must not use a local MinIO URL in {environment_name}",
            )

        if self.s3_access_key_id in LOCAL_S3_CREDENTIALS:
            errors.append(
                f"s3_access_key_id must not use the local MinIO default in {environment_name}",
            )

        if self.s3_secret_access_key in LOCAL_S3_CREDENTIALS:
            errors.append(
                "s3_secret_access_key must not use the local MinIO default "
                f"in {environment_name}",
            )

        if self.s3_bucket_name == "uploads":
            errors.append(
                f"s3_bucket_name must not use the local default in {environment_name}",
            )

        if self.redis_host in LOCAL_REDIS_HOSTS:
            errors.append(
                "redis_host must not use a local Docker or loopback host "
                f"in {environment_name}",
            )

        if self.redis_password.strip() == "":
            errors.append(f"redis_password is required in {environment_name}")

        if require_trusted_hosts:
            if not self.trusted_hosts_enabled:
                errors.append(
                    f"trusted_hosts_enabled must be true in {environment_name}",
                )

            if not parse_csv_setting(self.trusted_hosts):
                errors.append(f"trusted_hosts is required in {environment_name}")

            if not self.rate_limit_trust_forwarded_headers:
                errors.append(
                    "rate_limit_trust_forwarded_headers must be true "
                    f"in {environment_name}",
                )

        if self.cors_enabled and not parse_csv_setting(self.cors_allow_origins):
            errors.append(
                "cors_allow_origins is required when cors_enabled is true "
                f"in {environment_name}",
            )

        if self.cors_enabled and "*" in parse_csv_setting(self.cors_allow_origins):
            errors.append(
                "cors_allow_origins must not include a wildcard "
                f"in {environment_name}",
            )

        if require_webhook_secret:
            webhook_secret = self.webhook_signature_secret.strip()

            if webhook_secret == "":
                errors.append(
                    f"webhook_signature_secret is required in {environment_name}",
                )
            elif webhook_secret.lower() in WEAK_SECRET_KEYS:
                errors.append(
                    "webhook_signature_secret must not use a known weak placeholder "
                    f"in {environment_name}",
                )
            elif len(webhook_secret) < 32:
                errors.append(
                    "webhook_signature_secret must be at least 32 characters "
                    f"in {environment_name}",
                )

        if require_trusted_hosts and self.metrics_require_auth:
            if self.metrics_bearer_token.strip() == "":
                errors.append(
                    f"metrics_bearer_token is required in {environment_name}",
                )

        if self.twilio_account_sid.strip() or self.twilio_from_number.strip():
            if not self.twilio_auth_token.strip():
                errors.append(
                    f"twilio_auth_token is required when twilio_account_sid or "
                    f"twilio_from_number is set in {environment_name}",
                )

        if environment_name == "production":
            if not self.upload_malware_scan_enabled:
                errors.append(
                    "upload_malware_scan_enabled must be true in production",
                )

            if self.upload_malware_scanner_url.strip() == "":
                errors.append(
                    "upload_malware_scanner_url is required in production",
                )

        return errors

    @model_validator(mode="after")
    def apply_metrics_auth_default(self) -> "Settings":
        if self.metrics_require_auth is None:
            object.__setattr__(
                self,
                "metrics_require_auth",
                self.environment == "production",
            )

        return self

    @model_validator(mode="after")
    def apply_legacy_routes_default(self) -> "Settings":
        if self.legacy_routes_enabled is None:
            object.__setattr__(
                self,
                "legacy_routes_enabled",
                self.environment != "production",
            )

        return self

    @model_validator(mode="after")
    def validate_staging_settings(self) -> "Settings":
        secret_key = self.secret_key.strip()

        if secret_key.lower() in WEAK_SECRET_KEYS:
            raise ValueError("secret_key must not use a known weak placeholder")

        if self.environment != "staging":
            return self

        staging_errors = self._collect_remote_environment_errors(
            environment_name="staging",
            require_trusted_hosts=False,
            require_webhook_secret=False,
        )

        if staging_errors:
            raise ValueError("; ".join(staging_errors))

        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        secret_key = self.secret_key.strip()

        if secret_key.lower() in WEAK_SECRET_KEYS:
            raise ValueError("secret_key must not use a known weak placeholder")

        if self.environment != "production":
            return self

        production_errors = self._collect_remote_environment_errors(
            environment_name="production",
            require_trusted_hosts=True,
            require_webhook_secret=True,
        )

        if production_errors:
            raise ValueError("; ".join(production_errors))

        return self

    @model_validator(mode="after")
    def validate_worker_backoff(self) -> "Settings":
        if (
            self.worker_retry_backoff_max_seconds
            < self.worker_retry_backoff_base_seconds
        ):
            raise ValueError(
                "worker_retry_backoff_max_seconds must be greater than or equal to worker_retry_backoff_base_seconds",
            )

        return self

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("log_format")
    @classmethod
    def normalize_log_format(cls, value: str) -> str:
        normalized_log_format = value.lower()

        if normalized_log_format not in ALLOWED_LOG_FORMATS:
            allowed_values = ", ".join(sorted(ALLOWED_LOG_FORMATS))
            raise ValueError(f"log_format must be one of: {allowed_values}")

        return normalized_log_format

    @field_validator("redis_ssl_cert_reqs")
    @classmethod
    def normalize_redis_ssl_cert_reqs(cls, value: str) -> str:
        normalized_value = value.lower()

        if normalized_value not in ALLOWED_REDIS_SSL_CERT_REQS:
            allowed_values = ", ".join(sorted(ALLOWED_REDIS_SSL_CERT_REQS))
            raise ValueError(
                f"redis_ssl_cert_reqs must be one of: {allowed_values}",
            )

        return normalized_value

    def cors_origins_list(self) -> list[str]:
        return parse_csv_setting(self.cors_allow_origins)

    def cors_methods_list(self) -> list[str]:
        return parse_csv_setting(self.cors_allow_methods)

    def cors_headers_list(self) -> list[str]:
        return parse_csv_setting(self.cors_allow_headers)

    def trusted_hosts_list(self) -> list[str]:
        return parse_csv_setting(self.trusted_hosts)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
