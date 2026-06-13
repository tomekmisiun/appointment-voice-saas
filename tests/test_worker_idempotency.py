from app.core.redis import redis_client
from app.core.ids import uuid7
from app.core.job_queue import Job
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email_service import EmailDeliveryError
from app.services.password_reset_service import (
    create_password_reset_token_and_send_email,
    is_password_reset_job_completed,
    password_reset_job_completed_key,
)
from app.worker import handle_job


class FakeEmailService:
    def __init__(self):
        self.sent_password_reset_emails = []

    def send_password_reset_email(self, recipient: str, raw_token: str) -> None:
        self.sent_password_reset_emails.append(
            {"recipient": recipient, "raw_token": raw_token},
        )


def test_password_reset_email_job_is_idempotent_for_same_job_id(db, monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    user = User(
        email=f"idempotent-job-{uuid7().hex}@example.com",
        hashed_password="hashed",
        tenant_id=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job_id = str(uuid7())

    create_password_reset_token_and_send_email(db, user.id, job_id=job_id)
    create_password_reset_token_and_send_email(db, user.id, job_id=job_id)

    token_count = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .count()
    )

    assert token_count == 1
    assert len(email_service.sent_password_reset_emails) == 1
    assert is_password_reset_job_completed(job_id) is True


def test_password_reset_email_job_db_dedup_when_redis_marker_missing(
    db,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    user = User(
        email=f"db-dedup-{uuid7().hex}@example.com",
        hashed_password="hashed",
        tenant_id=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job_id = str(uuid7())

    create_password_reset_token_and_send_email(db, user.id, job_id=job_id)

    redis_client.delete(password_reset_job_completed_key(job_id))
    assert is_password_reset_job_completed(job_id) is False

    create_password_reset_token_and_send_email(db, user.id, job_id=job_id)

    token_count = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .count()
    )

    assert token_count == 1
    assert len(email_service.sent_password_reset_emails) == 1
    assert is_password_reset_job_completed(job_id) is True


def test_password_reset_email_job_retry_after_delivery_failure_sends_once(
    db,
    monkeypatch,
):
    class FlakyEmailService(FakeEmailService):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        def send_password_reset_email(self, recipient: str, raw_token: str) -> None:
            self.attempts += 1
            if self.attempts == 1:
                raise EmailDeliveryError("temporary smtp failure")
            super().send_password_reset_email(recipient, raw_token)

    email_service = FlakyEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    user = User(
        email=f"retry-job-{uuid7().hex}@example.com",
        hashed_password="hashed",
        tenant_id=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job_id = str(uuid7())

    try:
        create_password_reset_token_and_send_email(db, user.id, job_id=job_id)
    except EmailDeliveryError:
        db.rollback()

    assert is_password_reset_job_completed(job_id) is False

    create_password_reset_token_and_send_email(db, user.id, job_id=job_id)

    token_count = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .count()
    )

    assert token_count == 1
    assert len(email_service.sent_password_reset_emails) == 1
    assert is_password_reset_job_completed(job_id) is True


def test_handle_job_passes_job_id_to_password_reset_service(db, monkeypatch):
    captured: dict[str, str | None] = {"job_id": None}

    def fake_create_password_reset_token_and_send_email(
        session,
        user_id: int,
        *,
        job_id: str | None = None,
    ) -> None:
        captured["job_id"] = job_id

    monkeypatch.setattr(
        "app.worker.create_password_reset_token_and_send_email",
        fake_create_password_reset_token_and_send_email,
    )

    job = Job(
        id=str(uuid7()),
        type="send_password_reset_email",
        payload={"user_id": 123},
    )
    handle_job(job)

    assert captured["job_id"] == job.id
