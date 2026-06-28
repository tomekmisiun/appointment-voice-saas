import logging
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.sms import SmsMessage, SmsSendResult

logger = logging.getLogger("app.sms_provider")


class SmsProvider(Protocol):
    name: str

    def send(self, message: SmsMessage) -> SmsSendResult:
        ...


class NullSmsProvider:
    """Default provider used until a real or fake adapter is configured."""

    name = "null"

    def __init__(self, error: str = "sms_provider_not_configured") -> None:
        self._error = error

    def send(self, message: SmsMessage) -> SmsSendResult:
        _ = message
        return SmsSendResult(success=False, error=self._error)


class FakeSmsProvider:
    """Local/dev/test provider that records sent messages instead of delivering them."""

    name = "fake"

    def __init__(self) -> None:
        self.sent: list[SmsMessage] = []

    def send(self, message: SmsMessage) -> SmsSendResult:
        self.sent.append(message)
        return SmsSendResult(
            success=True, provider_message_id=f"fake-{len(self.sent)}"
        )


class TwilioSmsProvider:
    """Production SMS adapter backed by Twilio Messages API."""

    name = "twilio"
    _API_BASE = "https://api.twilio.com/2010-04-01/Accounts"

    def __init__(self, account_sid: str, auth_token: str, sms_from: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._sms_from = sms_from

    def send(self, message: SmsMessage) -> SmsSendResult:
        url = f"{self._API_BASE}/{self._account_sid}/Messages.json"
        try:
            resp = httpx.post(
                url,
                data={"From": self._sms_from, "To": message.to, "Body": message.body},
                auth=(self._account_sid, self._auth_token),
                timeout=10.0,
            )
            resp.raise_for_status()
            sid = resp.json().get("sid")
            return SmsSendResult(success=True, provider_message_id=sid)
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text[:200]
            logger.warning("twilio_sms_error status=%s body=%s", exc.response.status_code, error_detail)
            return SmsSendResult(success=False, error=f"twilio_http_{exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.warning("twilio_sms_request_error %s", exc)
            return SmsSendResult(success=False, error="twilio_request_error")


def get_sms_provider() -> SmsProvider:
    account_sid = settings.twilio_account_sid.strip()
    auth_token = settings.twilio_auth_token.strip()
    sms_from = settings.twilio_sms_from.strip()

    if account_sid and auth_token and sms_from:
        return TwilioSmsProvider(
            account_sid=account_sid,
            auth_token=auth_token,
            sms_from=sms_from,
        )
    if account_sid and auth_token:
        return NullSmsProvider("twilio_sms_from_not_configured")
    return NullSmsProvider()
