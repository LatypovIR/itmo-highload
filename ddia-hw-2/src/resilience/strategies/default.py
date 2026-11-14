from resilience.models.budget import Budget
from resilience.models.errors import BudgetExhaustedError
from resilience.models.outcome import Response, TimedOut
from resilience.models.strategy import ResilienceStrategy
from resilience.models.upstream import Upstream
from resilience.models.validation import require


class DefaultStrategy(ResilienceStrategy):
    def __init__(self, timeout: float) -> None:
        require(timeout > 0, "non-positive timeout")
        self._timeout = timeout

    async def run(self, upstream: Upstream) -> Response:
        outcome = await upstream.attempt(self._timeout)

        if isinstance(outcome, Response) and outcome.ok:
            return outcome

        exhausted = Budget.LATENCY if isinstance(outcome, TimedOut) else Budget.RETRIES

        raise BudgetExhaustedError(exhausted, [outcome])
