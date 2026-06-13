import uuid

from app.core import ids


def test_uuid7_returns_version_7_uuid():
    value = ids.uuid7()

    assert isinstance(value, uuid.UUID)
    assert value.version == 7
    assert value.variant == uuid.RFC_4122


def test_uuid7_fallback_returns_version_7_uuid(monkeypatch):
    monkeypatch.delattr(ids.uuid, "uuid7", raising=False)

    value = ids.uuid7()

    assert isinstance(value, uuid.UUID)
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
