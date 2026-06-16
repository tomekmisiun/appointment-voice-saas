from typing import Protocol

from app.core.calendar import CalendarEvent, CalendarResult


class CalendarProvider(Protocol):
    def create_event(self, event: CalendarEvent) -> CalendarResult:
        ...

    def update_event(self, provider_event_id: str, event: CalendarEvent) -> CalendarResult:
        ...

    def cancel_event(self, provider_event_id: str) -> CalendarResult:
        ...


class NullCalendarProvider:
    """Default provider used until a real or fake adapter is configured."""

    def create_event(self, event: CalendarEvent) -> CalendarResult:
        _ = event
        return CalendarResult(success=False, error="calendar_provider_not_configured")

    def update_event(self, provider_event_id: str, event: CalendarEvent) -> CalendarResult:
        _ = provider_event_id, event
        return CalendarResult(success=False, error="calendar_provider_not_configured")

    def cancel_event(self, provider_event_id: str) -> CalendarResult:
        _ = provider_event_id
        return CalendarResult(success=False, error="calendar_provider_not_configured")


class FakeCalendarProvider:
    """Local/dev/test provider that records calendar operations without network calls."""

    def __init__(self) -> None:
        self.created: list[CalendarEvent] = []
        self.updated: list[tuple[str, CalendarEvent]] = []
        self.cancelled: list[str] = []

    def create_event(self, event: CalendarEvent) -> CalendarResult:
        self.created.append(event)
        return CalendarResult(
            success=True, provider_event_id=f"fake-evt-{len(self.created)}"
        )

    def update_event(self, provider_event_id: str, event: CalendarEvent) -> CalendarResult:
        self.updated.append((provider_event_id, event))
        return CalendarResult(success=True, provider_event_id=provider_event_id)

    def cancel_event(self, provider_event_id: str) -> CalendarResult:
        self.cancelled.append(provider_event_id)
        return CalendarResult(success=True, provider_event_id=provider_event_id)


def get_calendar_provider() -> CalendarProvider:
    return NullCalendarProvider()
