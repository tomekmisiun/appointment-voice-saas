"""Tests for the calendar provider interface and fake provider (AVS-F001, AVS-F004)."""

from datetime import datetime, timezone

from app.core.calendar import CalendarEvent, CalendarResult
from app.services.calendar_provider import (
    CalendarProvider,
    FakeCalendarProvider,
    NullCalendarProvider,
    get_calendar_provider,
)


_EVENT = CalendarEvent(
    title="Haircut",
    starts_at=datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc),
    ends_at=datetime(2027, 9, 1, 9, 30, tzinfo=timezone.utc),
)


def test_null_calendar_provider_create_reports_not_configured():
    provider = NullCalendarProvider()
    result = provider.create_event(_EVENT)
    assert result.success is False
    assert result.error == "calendar_provider_not_configured"
    assert result.provider_event_id is None


def test_null_calendar_provider_update_reports_not_configured():
    provider = NullCalendarProvider()
    result = provider.update_event("evt-123", _EVENT)
    assert result.success is False
    assert result.error == "calendar_provider_not_configured"


def test_null_calendar_provider_cancel_reports_not_configured():
    provider = NullCalendarProvider()
    result = provider.cancel_event("evt-123")
    assert result.success is False
    assert result.error == "calendar_provider_not_configured"


def test_get_calendar_provider_returns_a_provider():
    provider = get_calendar_provider()
    assert isinstance(provider, NullCalendarProvider)


def test_custom_provider_satisfies_protocol():
    class _StubProvider:
        def create_event(self, event: CalendarEvent) -> CalendarResult:
            return CalendarResult(success=True, provider_event_id="stub-1")

        def update_event(self, provider_event_id: str, event: CalendarEvent) -> CalendarResult:
            return CalendarResult(success=True, provider_event_id=provider_event_id)

        def cancel_event(self, provider_event_id: str) -> CalendarResult:
            return CalendarResult(success=True)

    provider: CalendarProvider = _StubProvider()
    assert provider.create_event(_EVENT).success is True
    assert provider.update_event("evt-1", _EVENT).provider_event_id == "evt-1"
    assert provider.cancel_event("evt-1").success is True


# AVS-F004: FakeCalendarProvider


def test_fake_calendar_provider_starts_empty():
    provider = FakeCalendarProvider()

    assert provider.created == []
    assert provider.updated == []
    assert provider.cancelled == []


def test_fake_calendar_provider_create_records_event():
    provider: CalendarProvider = FakeCalendarProvider()

    result = provider.create_event(_EVENT)

    assert result.success is True
    assert result.provider_event_id == "fake-evt-1"
    assert provider.created == [_EVENT]


def test_fake_calendar_provider_create_increments_ids():
    provider = FakeCalendarProvider()
    second = CalendarEvent(
        title="Trim",
        starts_at=datetime(2027, 9, 2, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2027, 9, 2, 10, 30, tzinfo=timezone.utc),
    )

    provider.create_event(_EVENT)
    result = provider.create_event(second)

    assert result.provider_event_id == "fake-evt-2"
    assert provider.created == [_EVENT, second]


def test_fake_calendar_provider_update_records_change():
    provider = FakeCalendarProvider()

    result = provider.update_event("fake-evt-1", _EVENT)

    assert result.success is True
    assert result.provider_event_id == "fake-evt-1"
    assert provider.updated == [("fake-evt-1", _EVENT)]


def test_fake_calendar_provider_cancel_records_id():
    provider = FakeCalendarProvider()

    result = provider.cancel_event("fake-evt-1")

    assert result.success is True
    assert result.provider_event_id == "fake-evt-1"
    assert provider.cancelled == ["fake-evt-1"]
