from pydantic import BaseModel, Field

from app.core.ivr import IvrAction


class SimulateCallRequest(BaseModel):
    business_id: int
    caller_phone: str = Field(min_length=1, max_length=32)


class SimulatePressRequest(BaseModel):
    session_id: int
    key: str = Field(min_length=1, max_length=1)


class IvrOptionRead(BaseModel):
    key: str
    label: str


class IvrSessionResponse(BaseModel):
    session_id: int | None
    prompt: str
    options: list[IvrOptionRead]
    action: IvrAction
    transfer_destination: str | None = None
