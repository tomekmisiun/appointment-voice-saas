from app.core.job_queue import Job
from app.models.uploaded_file import UploadedFile, UploadVerificationStatus
from app.services.upload_verification_service import (
    VERIFY_PRESIGNED_UPLOAD_JOB,
    verify_presigned_upload_in_worker,
)
from app.worker import handle_job


def test_handle_job_processes_verify_presigned_upload(db, monkeypatch):
    uploaded_file = UploadedFile(
        tenant_id=1,
        owner_id=1,
        object_key="tenants/1/uploads/1/test.pdf",
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=4,
        verification_status=UploadVerificationStatus.pending,
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    calls = []

    monkeypatch.setattr(
        "app.worker.verify_presigned_upload_in_worker",
        lambda db, uploaded_file_id, storage_service=None: calls.append(
            uploaded_file_id
        ),
    )

    handle_job(
        Job(
            id="job-id",
            type=VERIFY_PRESIGNED_UPLOAD_JOB,
            payload={"uploaded_file_id": uploaded_file.id},
            attempts=0,
        )
    )

    assert calls == [uploaded_file.id]


def test_verify_presigned_upload_marks_file_verified(db, monkeypatch):
    uploaded_file = UploadedFile(
        tenant_id=1,
        owner_id=1,
        object_key="tenants/1/uploads/1/invoice.pdf",
        filename="invoice.pdf",
        content_type="application/pdf",
        size_bytes=16,
        verification_status=UploadVerificationStatus.pending,
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    class FakeStorageService:
        provider = object()

    monkeypatch.setattr(
        "app.services.upload_verification_service.verify_stored_object_content",
        lambda *args, **kwargs: None,
    )

    verify_presigned_upload_in_worker(
        db,
        uploaded_file_id=uploaded_file.id,
        storage_service=FakeStorageService(),
    )

    db.refresh(uploaded_file)
    assert uploaded_file.verification_status == UploadVerificationStatus.verified
