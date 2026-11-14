from collections.abc import Sequence

from resilience.models.budget import Budget
from resilience.models.outcome import Outcome


class ResilienceError(Exception):
    pass


class BudgetExhaustedError(ResilienceError):
    def __init__(self, budget: Budget, outcomes: Sequence[Outcome]) -> None:
        super().__init__(f"{budget} budget exhausted")
        self.budget = budget
        self.outcomes = tuple(outcomes)


class NoAvailableEndpointError(ResilienceError):
    def __init__(self) -> None:
        super().__init__("no available endpoint")
