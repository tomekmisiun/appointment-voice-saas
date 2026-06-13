import json
import sys

from app.core.job_queue import Job, move_job_to_failed_queue
from app.worker_failed_jobs import main
from tests.test_worker import FakeRedis


def test_worker_failed_jobs_list_outputs_json(monkeypatch, capsys):
    redis = FakeRedis()
    job = Job(
        id="job-id",
        type="send_password_reset_email",
        payload={"user_id": 123},
        attempts=3,
    )

    move_job_to_failed_queue(
        job,
        redis=redis,
        failed_queue_name="cli_failed_jobs",
    )

    monkeypatch.setattr(
        "app.worker_failed_jobs.list_failed_jobs",
        lambda limit=20: [job],
    )
    monkeypatch.setattr(sys, "argv", ["worker_failed_jobs", "list"])

    main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload[0]["id"] == "job-id"
    assert payload[0]["attempts"] == 3


def test_worker_failed_jobs_requeue_outputs_count(monkeypatch, capsys):
    monkeypatch.setattr(
        "app.worker_failed_jobs.requeue_failed_jobs",
        lambda limit=None: 2,
    )
    monkeypatch.setattr(sys, "argv", ["worker_failed_jobs", "requeue", "--limit", "2"])

    main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload == {"requeued": 2}
