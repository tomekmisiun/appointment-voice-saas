from datetime import datetime

from pydantic import BaseModel, Field


class UploadedFileRead(BaseModel):
    id: int
    owner_id: int
    object_key: str
    filename: str
    content_type: str
    size_bytes: int
    verification_status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class PresignedUploadRequest(BaseModel):
    filename: str = Field(examples=["invoice.pdf"])
    content_type: str = Field(examples=["application/pdf"])


class PresignedUploadResponse(BaseModel):
    object_key: str
    upload_url: str
    expires_in_seconds: int


class PresignedUploadCompleteRequest(BaseModel):
    object_key: str
    filename: str
    content_type: str
    size_bytes: int = Field(gt=0)


class PresignedDownloadUrlRead(BaseModel):
    download_url: str
    expires_in_seconds: int
