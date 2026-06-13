import hashlib
import hmac
import re
import time


class WebhookSignatureError(ValueError):
    pass


STRIPE_STYLE_SIGNATURE_PATTERN = re.compile(
    r"^t=(?P<timestamp>\d+)(?:,v1=(?P<signature>[a-f0-9]+))?$",
    re.IGNORECASE,
)


def hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_timestamped_signing_message(timestamp: int, payload: bytes) -> bytes:
    return f"{timestamp}.".encode("utf-8") + payload


def compute_hmac_signature(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def compute_timestamped_hmac_signature(
    timestamp: int,
    payload: bytes,
    secret: str,
) -> str:
    signing_message = build_timestamped_signing_message(timestamp, payload)
    return compute_hmac_signature(signing_message, secret)


def parse_webhook_signature_header(signature: str) -> tuple[int | None, str]:
    normalized_signature = signature.strip()

    stripe_match = STRIPE_STYLE_SIGNATURE_PATTERN.fullmatch(normalized_signature)
    if stripe_match is not None:
        timestamp = int(stripe_match.group("timestamp"))
        parsed_signature = stripe_match.group("signature")

        if parsed_signature is None:
            raise WebhookSignatureError("Webhook signature version is required")

        return timestamp, parsed_signature.lower()

    return None, normalized_signature.lower()


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> None:
    if not secret:
        raise WebhookSignatureError("Webhook signature secret is not configured")

    expected_signature = compute_hmac_signature(payload, secret)

    if not hmac.compare_digest(expected_signature, signature.lower()):
        raise WebhookSignatureError("Invalid webhook signature")


def verify_timestamped_hmac_signature(
    *,
    payload: bytes,
    signature: str,
    timestamp: int | None,
    secret: str,
    tolerance_seconds: int,
    now: int | None = None,
) -> int:
    if not secret:
        raise WebhookSignatureError("Webhook signature secret is not configured")

    header_timestamp, parsed_signature = parse_webhook_signature_header(signature)
    effective_timestamp = timestamp if timestamp is not None else header_timestamp

    if effective_timestamp is None:
        raise WebhookSignatureError("Webhook timestamp is required")

    current_timestamp = now if now is not None else int(time.time())
    age_seconds = abs(current_timestamp - effective_timestamp)

    if age_seconds > tolerance_seconds:
        raise WebhookSignatureError("Webhook timestamp is outside the replay window")

    signing_message = build_timestamped_signing_message(effective_timestamp, payload)
    expected_signature = compute_hmac_signature(signing_message, secret)

    if not hmac.compare_digest(expected_signature, parsed_signature):
        raise WebhookSignatureError("Invalid webhook signature")

    return effective_timestamp
