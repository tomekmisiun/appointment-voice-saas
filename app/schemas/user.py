from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class UserRole(StrEnum):
    user = "user"
    admin = "admin"
    platform_admin = "platform_admin"


class UserSearchMode(StrEnum):
    prefix = "prefix"
    contains = "contains"


class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: str
    is_demo_user: bool

    model_config = {
        "from_attributes": True,
    }


class UserListPage(BaseModel):
    items: list[UserRead]
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next keyset page, when available.",
    )


class UserSelfUpdate(BaseModel):
    email: EmailStr | None = None


class UserAdminUpdate(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = None
    role: UserRole | None = None
