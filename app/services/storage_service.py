from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
)
from app.core.file_validation import (
    ensure_malware_scan_is_clean,
    run_malware_scan,
    validate_content_sniff,
    validate_declared_content_type,
)
from app.core.ids import uuid7
from app.core.permissions import Permission
from app.core.s3_client import get_s3_client
from app.core.upload_metadata import validate_upload_filename
from app.models.uploaded_file import UploadedFile, UploadVerificationStatus
from app.models.user import User
from app.services.permission_service import user_has_permission
from app.services.tenant_service import build_tenant_object_key_prefix


@dataclass(frozen=True)
class StoredObjectMetadata:
    size_bytes: int
    content_type: str


@dataclass(frozen=True)
class PresignedUrl:
    url: str
    expires_in_seconds: int


class S3StorageProvider:
    def __init__(self, client=None):
        self.client = client or get_s3_client()

    def upload_file(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
    ) -> None:
        self.client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=body,
            ContentType=content_type,
        )

    def upload_fileobj(
        self,
        *,
        object_key: str,
        fileobj: BinaryIO,
        content_type: str,
    ) -> None:
        self.client.upload_fileobj(
            fileobj,
            settings.s3_bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def delete_object(self, *, object_key: str) -> None:
        self.client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
        )

    def object_exists(self, *, object_key: str) -> bool:
        try:
            self.client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=object_key,
            )
        except ClientError:
            return False

        return True

    def get_object_metadata(self, *, object_key: str) -> StoredObjectMetadata:
        try:
            response = self.client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            raise BadRequestError(
                "Uploaded object was not found in storage",
            ) from exc

        content_type = response.get("ContentType") or "application/octet-stream"

        return StoredObjectMetadata(
            size_bytes=int(response["ContentLength"]),
            content_type=content_type.split(";", maxsplit=1)[0].strip().lower(),
        )

    def download_object_body(self, *, object_key: str, max_bytes: int) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            raise BadRequestError(
                "Uploaded object could not be verified",
            ) from exc

        body = response["Body"].read(max_bytes + 1)

        if len(body) > max_bytes:
            raise PayloadTooLargeError("File too large")

        return body

    def generate_presigned_download_url(self, *, object_key: str) -> PresignedUrl:
        url = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": object_key,
            },
            ExpiresIn=settings.upload_presigned_url_expire_seconds,
        )

        return PresignedUrl(
            url=url,
            expires_in_seconds=settings.upload_presigned_url_expire_seconds,
        )

    def generate_presigned_upload_url(
        self,
        *,
        object_key: str,
        content_type: str,
    ) -> PresignedUrl:
        url = self.client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.upload_presigned_url_expire_seconds,
        )

        return PresignedUrl(
            url=url,
            expires_in_seconds=settings.upload_presigned_url_expire_seconds,
        )

    def verify_bucket_access(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.s3_bucket_name)
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError(
                "Object storage bucket is not reachable",
            ) from exc


class StorageService:
    def __init__(self, provider: S3StorageProvider | None = None):
        self.provider = provider or S3StorageProvider()

    def upload(
        self,
        *,
        owner: User,
        file: UploadFile,
        db: Session,
    ) -> UploadedFile:
        filename = validate_upload_filename(file.filename or "upload")
        content_type = validate_declared_content_type(
            file.content_type or "application/octet-stream",
        )
        spool, size_bytes = spool_upload_stream_limited(file)
        validate_file_size(size_bytes)

        sniff_prefix = spool.read(512)
        spool.seek(0)
        validate_content_sniff(content_type, sniff_prefix)

        scan_body = spool.read()
        spool.seek(0)
        ensure_malware_scan_is_clean(run_malware_scan(scan_body, filename))

        object_key = build_object_key(owner.tenant_id, owner.id, filename)

        try:
            self.provider.upload_fileobj(
                object_key=object_key,
                fileobj=spool,
                content_type=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError("Object storage upload failed") from exc
        finally:
            spool.close()

        uploaded_file = UploadedFile(
            tenant_id=owner.tenant_id,
            owner_id=owner.id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            verification_status=UploadVerificationStatus.verified,
        )

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        return uploaded_file

    def create_presigned_upload(
        self,
        *,
        owner: User,
        filename: str,
        content_type: str,
    ) -> tuple[str, PresignedUrl]:
        safe_filename = validate_upload_filename(filename)
        normalized_content_type = validate_declared_content_type(content_type)
        self.provider.verify_bucket_access()
        object_key = build_object_key(owner.tenant_id, owner.id, safe_filename)
        presigned_url = self.provider.generate_presigned_upload_url(
            object_key=object_key,
            content_type=normalized_content_type,
        )

        return object_key, presigned_url

    def complete_presigned_upload(
        self,
        *,
        owner: User,
        object_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        db: Session,
    ) -> UploadedFile:
        safe_filename = validate_upload_filename(filename)
        normalized_content_type = validate_declared_content_type(content_type)
        validate_file_size(size_bytes)
        ensure_object_key_belongs_to_owner(
            object_key=object_key,
            owner=owner,
        )

        verify_stored_object_metadata(
            self.provider,
            object_key=object_key,
            declared_content_type=normalized_content_type,
            declared_size_bytes=size_bytes,
        )

        uploaded_file = UploadedFile(
            tenant_id=owner.tenant_id,
            owner_id=owner.id,
            object_key=object_key,
            filename=safe_filename,
            content_type=normalized_content_type,
            size_bytes=size_bytes,
            verification_status=UploadVerificationStatus.pending,
        )

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        from app.services.upload_verification_service import (
            enqueue_verify_presigned_upload_job,
        )

        enqueue_verify_presigned_upload_job(uploaded_file.id)

        return uploaded_file

    def get_presigned_download_url(
        self,
        *,
        uploaded_file: UploadedFile,
        current_user: User,
    ) -> PresignedUrl:
        if not can_access_uploaded_file(current_user, uploaded_file):
            raise ForbiddenError("Insufficient permissions")

        ensure_upload_is_downloadable(uploaded_file)

        try:
            return self.provider.generate_presigned_download_url(
                object_key=uploaded_file.object_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError(
                "Object storage download URL generation failed",
            ) from exc

    def delete_uploaded_file(
        self,
        *,
        uploaded_file: UploadedFile,
        current_user: User,
        db: Session,
    ) -> None:
        if not can_delete_uploaded_file(current_user, uploaded_file):
            raise ForbiddenError("Insufficient permissions")

        try:
            self.provider.delete_object(object_key=uploaded_file.object_key)
        except (BotoCoreError, ClientError) as exc:
            raise ServiceUnavailableError("Object storage delete failed") from exc

        db.delete(uploaded_file)
        db.commit()

    def verify_bucket_access(self) -> None:
        self.provider.verify_bucket_access()


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service

    if _storage_service is None:
        _storage_service = StorageService()

    return _storage_service


def reset_storage_service_cache() -> None:
    global _storage_service
    _storage_service = None


def get_uploaded_file(
    db: Session,
    *,
    file_id: int,
    tenant_id: int,
) -> UploadedFile | None:
    return (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == file_id,
            UploadedFile.tenant_id == tenant_id,
        )
        .first()
    )


def can_access_uploaded_file(current_user: User, uploaded_file: UploadedFile) -> bool:
    if current_user.tenant_id != uploaded_file.tenant_id:
        return False

    if user_has_permission(current_user, Permission.FILES_DOWNLOAD):
        return True

    return (
        uploaded_file.owner_id == current_user.id
        and user_has_permission(current_user, Permission.FILES_DOWNLOAD_SELF)
    )


def can_delete_uploaded_file(current_user: User, uploaded_file: UploadedFile) -> bool:
    if current_user.tenant_id != uploaded_file.tenant_id:
        return False

    if user_has_permission(current_user, Permission.FILES_DELETE):
        return True

    return (
        uploaded_file.owner_id == current_user.id
        and user_has_permission(current_user, Permission.FILES_DELETE_SELF)
    )


def ensure_upload_is_downloadable(uploaded_file: UploadedFile) -> None:
    if uploaded_file.verification_status == UploadVerificationStatus.pending:
        raise ConflictError("File verification is still in progress")

    if uploaded_file.verification_status != UploadVerificationStatus.verified:
        raise NotFoundError("File not found")


def validate_file_size(size_bytes: int) -> None:
    if size_bytes > settings.upload_max_size_bytes:
        raise PayloadTooLargeError("File too large")


def spool_upload_stream_limited(file: UploadFile) -> tuple[SpooledTemporaryFile, int]:
    chunk_size = settings.upload_stream_chunk_size_bytes
    total_size = 0
    spool = SpooledTemporaryFile(max_size=settings.upload_spool_max_memory_bytes)

    while True:
        chunk = file.file.read(chunk_size)

        if not chunk:
            break

        total_size += len(chunk)

        if total_size > settings.upload_max_size_bytes:
            spool.close()
            raise PayloadTooLargeError("File too large")

        spool.write(chunk)

    spool.seek(0)
    return spool, total_size


def read_upload_body_limited(file: UploadFile) -> bytes:
    spool, _total_size = spool_upload_stream_limited(file)

    try:
        return spool.read()
    finally:
        spool.close()


def verify_stored_object_metadata(
    provider: S3StorageProvider,
    *,
    object_key: str,
    declared_content_type: str,
    declared_size_bytes: int,
) -> StoredObjectMetadata:
    metadata = provider.get_object_metadata(object_key=object_key)
    assert_stored_metadata_matches(
        metadata=metadata,
        declared_content_type=declared_content_type,
        declared_size_bytes=declared_size_bytes,
    )

    return metadata


def verify_stored_object_content(
    provider: S3StorageProvider,
    *,
    object_key: str,
    declared_content_type: str,
    declared_size_bytes: int,
    filename: str,
) -> None:
    metadata = provider.get_object_metadata(object_key=object_key)
    assert_stored_metadata_matches(
        metadata=metadata,
        declared_content_type=declared_content_type,
        declared_size_bytes=declared_size_bytes,
    )

    body = provider.download_object_body(
        object_key=object_key,
        max_bytes=metadata.size_bytes,
    )

    if len(body) != metadata.size_bytes:
        raise BadRequestError("Uploaded object size could not be verified")

    validate_content_sniff(declared_content_type, body)
    ensure_malware_scan_is_clean(run_malware_scan(body, filename))


def verify_stored_object(
    provider: S3StorageProvider,
    *,
    object_key: str,
    declared_content_type: str,
    declared_size_bytes: int,
    filename: str,
) -> None:
    verify_stored_object_content(
        provider,
        object_key=object_key,
        declared_content_type=declared_content_type,
        declared_size_bytes=declared_size_bytes,
        filename=filename,
    )


def assert_stored_metadata_matches(
    *,
    metadata: StoredObjectMetadata,
    declared_content_type: str,
    declared_size_bytes: int,
) -> None:
    if metadata.size_bytes != declared_size_bytes:
        raise BadRequestError(
            "Uploaded object size does not match declared size",
        )

    if metadata.content_type != declared_content_type:
        raise BadRequestError(
            "Uploaded object content type does not match declared content type",
        )


def build_object_key(tenant_id: int, owner_id: int, filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    tenant_prefix = build_tenant_object_key_prefix(tenant_id)
    return f"{tenant_prefix}/uploads/{owner_id}/{uuid7().hex}-{safe_filename}"


def ensure_object_key_belongs_to_owner(*, object_key: str, owner: User) -> None:
    expected_prefix = (
        f"{build_tenant_object_key_prefix(owner.tenant_id)}/uploads/{owner.id}/"
    )

    if not object_key.startswith(expected_prefix):
        raise BadRequestError("Invalid object key for current user")
