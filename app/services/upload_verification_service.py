import logging

from sqlalchemy.orm import Session

from app.core.domain_errors import DomainError
from app.core.job_queue import Job, enqueue_job
from app.models.uploaded_file import UploadedFile, UploadVerificationStatus
from app.services.storage_service import (
    get_storage_service,
    verify_stored_object_content,
)


logger = logging.getLogger("app.upload_verification")

VERIFY_PRESIGNED_UPLOAD_JOB = "verify_presigned_upload"


def enqueue_verify_presigned_upload_job(uploaded_file_id: int) -> Job:
    return enqueue_job(
        VERIFY_PRESIGNED_UPLOAD_JOB,
        {"uploaded_file_id": uploaded_file_id},
    )


def verify_presigned_upload_in_worker(
    db: Session,
    *,
    uploaded_file_id: int,
    storage_service=None,
) -> None:
    uploaded_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == uploaded_file_id)
        .first()
    )

    if uploaded_file is None:
        return

    if uploaded_file.verification_status != UploadVerificationStatus.pending:
        return

    storage_service = storage_service or get_storage_service()

    try:
        verify_stored_object_content(
            storage_service.provider,
            object_key=uploaded_file.object_key,
            declared_content_type=uploaded_file.content_type,
            declared_size_bytes=uploaded_file.size_bytes,
            filename=uploaded_file.filename,
        )
    except DomainError as exc:
        logger.warning(
            "presigned_upload_verification_failed uploaded_file_id=%s detail=%s",
            uploaded_file.id,
            exc.message,
        )

        try:
            storage_service.provider.delete_object(object_key=uploaded_file.object_key)
        except Exception:
            logger.exception(
                "presigned_upload_verification_cleanup_failed uploaded_file_id=%s",
                uploaded_file.id,
            )

        db.delete(uploaded_file)
        db.commit()
        return

    uploaded_file.verification_status = UploadVerificationStatus.verified
    db.commit()
