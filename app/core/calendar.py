from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    starts_at: datetime
    ends_at: datetime
    description: str = ""


@dataclass(frozen=True)
class CalendarResult:
    success: bool
    provider_event_id: str | None = None
    error: str | None = None
