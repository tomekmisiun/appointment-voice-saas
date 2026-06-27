from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_non_demo_user, require_permission
from app.api.openapi import PROTECTED_ERROR_RESPONSES
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.file import (
    PresignedDownloadUrlRead,
    PresignedUploadCompleteRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
    UploadedFileRead,
)
from app.services.storage_service import (
    get_storage_service,
    get_uploaded_file,
)


router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=UploadedFileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description=(
        "Authenticated multipart upload with size, declared content-type, and "
        "content-sniff validation. Objects are stored privately in "
        "S3-compatible storage."
    ),
    responses=PROTECTED_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.FILES_UPLOAD)),
):
    return get_storage_service().upload(
        owner=current_user,
        file=file,
        db=db,
    )


@router.post(
    "/presigned-upload",
    response_model=PresignedUploadResponse,
    summary="Create a presigned upload URL",
    description=(
        "Returns a short-lived private PUT URL for direct client-side uploads."
    ),
    responses=PROTECTED_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def create_presigned_upload(
    upload_request: PresignedUploadRequest,
    current_user: User = Depends(require_permission(Permission.FILES_UPLOAD)),
):
    object_key, presigned_url = get_storage_service().create_presigned_upload(
        owner=current_user,
        filename=upload_request.filename,
        content_type=upload_request.content_type,
    )

    return PresignedUploadResponse(
        object_key=object_key,
        upload_url=presigned_url.url,
        expires_in_seconds=presigned_url.expires_in_seconds,
    )


@router.post(
    "/presigned-upload/complete",
    response_model=UploadedFileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a presigned upload",
    responses=PROTECTED_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def complete_presigned_upload(
    upload_complete: PresignedUploadCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.FILES_UPLOAD)),
):
    return get_storage_service().complete_presigned_upload(
        owner=current_user,
        object_key=upload_complete.object_key,
        filename=upload_complete.filename,
        content_type=upload_complete.content_type,
        size_bytes=upload_complete.size_bytes,
        db=db,
    )


@router.get(
    "/{file_id}/download-url",
    response_model=PresignedDownloadUrlRead,
    summary="Get a presigned download URL",
    responses=PROTECTED_ERROR_RESPONSES,
)
def get_download_url(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uploaded_file = get_uploaded_file(
        db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if uploaded_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    presigned_url = get_storage_service().get_presigned_download_url(
        uploaded_file=uploaded_file,
        current_user=current_user,
    )

    return PresignedDownloadUrlRead(
        download_url=presigned_url.url,
        expires_in_seconds=presigned_url.expires_in_seconds,
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an uploaded file",
    responses=PROTECTED_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uploaded_file = get_uploaded_file(
        db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if uploaded_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    get_storage_service().delete_uploaded_file(
        uploaded_file=uploaded_file,
        current_user=current_user,
        db=db,
    )
