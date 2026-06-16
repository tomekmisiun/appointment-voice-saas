import base64
import hashlib
import hmac


class TwilioSignatureError(ValueError):
    pass


def verify_twilio_signature(
    *,
    url: str,
    form_data: dict[str, str],
    signature: str,
    auth_token: str,
) -> None:
    """Verify X-Twilio-Signature using Twilio's HMAC-SHA1 scheme.

    Raises TwilioSignatureError on invalid or missing signatures.
    Skips verification when auth_token is empty (dev/test mode).
    """
    if not auth_token:
        return

    s = url + "".join(k + form_data[k] for k in sorted(form_data))
    mac = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode()

    if not hmac.compare_digest(expected, signature):
        raise TwilioSignatureError("Invalid Twilio signature")
