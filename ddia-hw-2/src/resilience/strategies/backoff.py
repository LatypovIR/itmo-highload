import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from resilience.models.outcome import Outcome, OutcomeKind
from resilience.models.validation import require


class Backoff(ABC):
    @abstractmethod
    def next_delay(self, outcomes: Sequence[Outcome]) -> float: ...


class NoBackoff(Backoff):
    def next_delay(self, outcomes: Sequence[Outcome]) -> float:
        return 0.0


@dataclass(frozen=True)
class ExponentialBackoff(Backoff):
    initial_delay: float
    max_delay: float = math.inf

    def __post_init__(self) -> None:
        require(self.initial_delay > 0, "non-positive initial_delay")
        require(self.max_delay >= self.initial_delay, "max_delay below initial_delay")

    def next_delay(self, outcomes: Sequence[Outcome]) -> float:
        if not _is_slow_failure(outcomes[-1]):
            return 0.0

        slow_failures = sum(_is_slow_failure(outcome) for outcome in outcomes)
        delay = self.initial_delay * 2.0 ** (slow_failures - 1)

        return min(delay, self.max_delay)


def _is_slow_failure(outcome: Outcome) -> bool:
    return outcome.kind in (OutcomeKind.SERVER_ERROR, OutcomeKind.TIMEOUT)
