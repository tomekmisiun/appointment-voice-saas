from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(
        examples=["unauthorized"],
        description="Stable machine-readable error code.",
    )
    message: str = Field(
        examples=["Could not validate credentials"],
        description="Human-readable error message safe for API clients.",
    )
    details: list | dict | None = Field(
        default=None,
        description="Optional structured validation or context details.",
    )


class ErrorResponse(BaseModel):
    error: ErrorBody

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "Could not validate credentials",
                    }
                }
            ]
        }
    }
