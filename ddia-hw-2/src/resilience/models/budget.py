import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from resilience.models.outcome import Outcome, OutcomeKind
from resilience.models.validation import require


class Budget(StrEnum):
    RETRIES = "retries"
    FAST_ERRORS = "fast_errors"
    FAILURES = "failures"
    TIMEOUTS = "timeouts"
    LATENCY = "latency"


@dataclass(frozen=True)
class RetryBudget:
    max_retries: int
    fast_errors: int = 1
    failures: int = 1
    timeouts: int = 1

    def __post_init__(self) -> None:
        require(self.max_retries >= 1, "max_retries below 1")
        require(self.fast_errors >= 1, "fast_errors below 1")
        require(self.failures >= 1, "failures below 1")
        require(self.timeouts >= 1, "timeouts below 1")

    def exhausted_by(self, outcomes: Sequence[Outcome]) -> Budget | None:
        last_kind = outcomes[-1].kind
        errors = sum(outcome.kind is last_kind for outcome in outcomes)

        match last_kind:
            case OutcomeKind.CLIENT_ERROR if errors >= self.fast_errors:
                return Budget.FAST_ERRORS
            case OutcomeKind.SERVER_ERROR if errors >= self.failures:
                return Budget.FAILURES
            case OutcomeKind.TIMEOUT if errors >= self.timeouts:
                return Budget.TIMEOUTS

        if len(outcomes) >= self.max_retries:
            return Budget.RETRIES

        return None


@dataclass(frozen=True)
class LatencyBudget:
    total: float
    per_attempt: float = math.inf

    def __post_init__(self) -> None:
        require(self.total > 0, "non-positive total")
        require(self.per_attempt > 0, "non-positive per_attempt")
