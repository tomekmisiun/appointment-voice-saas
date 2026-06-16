"""Tests for the calendar provider interface (AVS-F001)."""

from datetime import datetime, timezone

from app.core.calendar import CalendarEvent, CalendarResult
from app.services.calendar_provider import (
    CalendarProvider,
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
