from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(min_length=8, examples=["strong-password"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "strong-password",
                }
            ]
        }
    }


class UserLogin(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(examples=["strong-password"])


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, examples=["reset-token-from-email"])
    new_password: str = Field(min_length=8, examples=["new-strong-password"])


class MessageResponse(BaseModel):
    message: str
