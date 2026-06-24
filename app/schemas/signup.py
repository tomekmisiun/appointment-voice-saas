from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.tenant import TENANT_SLUG_PATTERN, TenantRead
from app.schemas.user import UserRead


class TenantSignupRequest(BaseModel):
    salon_name: str = Field(min_length=1, max_length=255, examples=["Glamour Studio"])
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=63,
        examples=["glamour-studio"],
        description="Optional. Auto-generated from salon_name when omitted.",
    )
    admin_email: EmailStr = Field(examples=["owner@example.com"])
    admin_password: str = Field(min_length=8, examples=["strong-password"])

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not TENANT_SLUG_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Slug must contain lowercase letters, numbers, and hyphens only"
            )
        return normalized


class TenantSignupResponse(BaseModel):
    tenant: TenantRead
    user: UserRead
