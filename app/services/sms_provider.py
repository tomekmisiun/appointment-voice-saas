from typing import Protocol

from app.core.sms import SmsMessage, SmsSendResult


class SmsProvider(Protocol):
    def send(self, message: SmsMessage) -> SmsSendResult:
        ...


class NullSmsProvider:
    """Default provider used until a real or fake adapter is configured."""

    def send(self, message: SmsMessage) -> SmsSendResult:
        _ = message
        return SmsSendResult(success=False, error="sms_provider_not_configured")


class FakeSmsProvider:
    """Local/dev/test provider that records sent messages instead of delivering them."""

    def __init__(self) -> None:
        self.sent: list[SmsMessage] = []

    def send(self, message: SmsMessage) -> SmsSendResult:
        self.sent.append(message)
        return SmsSendResult(
            success=True, provider_message_id=f"fake-{len(self.sent)}"
        )


def get_sms_provider() -> SmsProvider:
    return NullSmsProvider()
