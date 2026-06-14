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


def get_sms_provider() -> SmsProvider:
    return NullSmsProvider()
