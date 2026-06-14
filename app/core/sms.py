from dataclasses import dataclass


@dataclass(frozen=True)
class SmsMessage:
    to: str
    body: str


@dataclass(frozen=True)
class SmsSendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None
