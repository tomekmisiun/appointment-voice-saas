import re

from pydantic import BaseModel, Field, field_validator

TENANT_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=63, examples=["acme-corp"])
    name: str = Field(min_length=1, max_length=255, examples=["Acme Corp"])

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.strip().lower()

        if not TENANT_SLUG_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Slug must contain lowercase letters, numbers, and hyphens only"
            )

        return normalized


class TenantRead(BaseModel):
    id: int
    slug: str
    name: str
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
