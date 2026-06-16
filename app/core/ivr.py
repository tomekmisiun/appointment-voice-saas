from dataclasses import dataclass, field
from enum import StrEnum


class IvrAction(StrEnum):
    CONTINUE = "continue"
    END = "end"
    TRANSFER = "transfer"


@dataclass(frozen=True)
class IvrOption:
    key: str
    label: str


@dataclass(frozen=True)
class IvrResponse:
    prompt: str
    options: tuple[IvrOption, ...] = field(default_factory=tuple)
    action: IvrAction = IvrAction.CONTINUE
    session_id: int | None = None
