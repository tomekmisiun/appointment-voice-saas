"""Tests for the SMS provider interface (AVS-E002)."""

from app.core.sms import SmsMessage, SmsSendResult
from app.services.sms_provider import NullSmsProvider, SmsProvider, get_sms_provider


def test_null_sms_provider_reports_not_configured():
    provider: SmsProvider = NullSmsProvider()

    result = provider.send(SmsMessage(to="+48600100200", body="hello"))

    assert isinstance(result, SmsSendResult)
    assert result.success is False
    assert result.error == "sms_provider_not_configured"
    assert result.provider_message_id is None


def test_get_sms_provider_returns_a_provider_by_default():
    provider = get_sms_provider()

    assert isinstance(provider, NullSmsProvider)


def test_custom_provider_satisfies_protocol():
    class RecordingProvider:
        def __init__(self):
            self.sent: list[SmsMessage] = []

        def send(self, message: SmsMessage) -> SmsSendResult:
            self.sent.append(message)
            return SmsSendResult(success=True, provider_message_id="msg-1")

    provider: SmsProvider = RecordingProvider()
    message = SmsMessage(to="+48600100200", body="hello")

    result = provider.send(message)

    assert result.success is True
    assert result.provider_message_id == "msg-1"
    assert provider.sent == [message]
