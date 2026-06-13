from pydantic import BaseModel, Field


class WebhookInboundRequest(BaseModel):
    provider: str = Field(examples=["payments"])
    event_id: str = Field(examples=["evt_123"])
    event_type: str = Field(examples=["payment.succeeded"])
    payload: dict = Field(examples=[{"amount": 1000, "currency": "usd"}])


class WebhookInboundResponse(BaseModel):
    status: str
    provider: str
    event_id: str
