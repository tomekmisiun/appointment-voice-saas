from datetime import datetime

from pydantic import BaseModel


class AvailabilitySlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
