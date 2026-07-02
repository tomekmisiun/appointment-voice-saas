"""Public booking management via HMAC-signed tokens (PUBLIC-LINK).

Token format: ``{booking_id}.{exp_unix}.{hmac_hex}``

The HMAC is keyed with ``SECRET_KEY + ":booking_management"`` and signs
``"{booking_id}:{exp_unix}"`` so the expiry is tamper-proof.  Tokens are
stateless but carry a 90-day TTL from generation.  An old token stops
working after expiry *or* when the booking reaches a terminal state, or
when SECRET_KEY is rotated.

The public URL looks like:
  https://example.com/manage-booking/42.1753920000.abc123…
"""

import hashlib
import hmac as _hmac
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.models.booking import Booking, BookingStatus

BOOKING_TOKEN_TTL_SECONDS = 90 * 24 * 3600  # 90 days


def _signing_key() -> bytes:
    return (settings.secret_key + ":booking_management").encode()


def _sign(booking_id: int, exp_unix: int) -> str:
    return _hmac.new(
        _signing_key(),
        msg=f"{booking_id}:{exp_unix}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def generate_booking_token(booking_id: int) -> str:
    exp_unix = int(time.time()) + BOOKING_TOKEN_TTL_SECONDS
    sig = _sign(booking_id, exp_unix)
    return f"{booking_id}.{exp_unix}.{sig}"


def verify_booking_token(token: str) -> int:
    """Return booking_id if the token is valid and unexpired; raise ValueError otherwise."""
    try:
        raw_id, raw_exp, sig = token.split(".", 2)
        booking_id = int(raw_id)
        exp_unix = int(raw_exp)
    except (ValueError, AttributeError):
        raise ValueError("Invalid token format")

    expected = _sign(booking_id, exp_unix)
    if not _hmac.compare_digest(expected, sig):
        raise ValueError("Invalid token signature")

    if time.time() > exp_unix:
        raise ValueError("Token has expired")

    return booking_id


def get_booking_by_public_token(db: Session, token: str) -> Booking:
    """Verify the token and return the associated Booking, or raise NotFoundError."""
    try:
        booking_id = verify_booking_token(token)
    except ValueError:
        raise NotFoundError("booking")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise NotFoundError("booking")

    return booking


def build_public_management_url(booking_id: int) -> str | None:
    """Return the full public management URL, or None if not configured."""
    base = settings.booking_public_base_url.rstrip("/")
    if not base:
        return None
    token = generate_booking_token(booking_id)
    return f"{base}/{token}"
