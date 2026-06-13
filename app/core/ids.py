import secrets
import time
import uuid


def uuid7() -> uuid.UUID:
    stdlib_uuid7 = getattr(uuid, "uuid7", None)

    if stdlib_uuid7 is not None:
        return stdlib_uuid7()

    timestamp_ms = (time.time_ns() // 1_000_000) & ((1 << 48) - 1)
    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)

    uuid_int = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )

    return uuid.UUID(int=uuid_int)
