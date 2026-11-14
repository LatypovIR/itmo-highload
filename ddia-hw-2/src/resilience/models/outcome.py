from dataclasses import dataclass
from enum import StrEnum


class OutcomeKind(StrEnum):
    SUCCESS = "success"
    CLIENT_ERROR = "client_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"

    @classmethod
    def from_status(cls, status: int) -> "OutcomeKind":
        match status // 100:
            case 2:
                return cls.SUCCESS
            case 4:
                return cls.CLIENT_ERROR
            case 5:
                return cls.SERVER_ERROR
            case _:
                raise ValueError(f"unsupported status {status}")


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = b""

    def __post_init__(self) -> None:
        OutcomeKind.from_status(self.status)

    @property
    def kind(self) -> OutcomeKind:
        return OutcomeKind.from_status(self.status)

    @property
    def ok(self) -> bool:
        return self.kind is OutcomeKind.SUCCESS


@dataclass(frozen=True)
class TimedOut:
    @property
    def kind(self) -> OutcomeKind:
        return OutcomeKind.TIMEOUT


Outcome = Response | TimedOut
