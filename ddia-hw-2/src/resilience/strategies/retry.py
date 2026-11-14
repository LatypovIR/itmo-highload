import asyncio

from resilience.models.budget import Budget, LatencyBudget, RetryBudget
from resilience.models.errors import BudgetExhaustedError
from resilience.models.outcome import Outcome, Response
from resilience.models.strategy import ResilienceStrategy
from resilience.models.upstream import Upstream
from resilience.strategies.backoff import Backoff, NoBackoff


class RetryStrategy(ResilienceStrategy):
    def __init__(
        self,
        retry_budget: RetryBudget,
        latency_budget: LatencyBudget,
        backoff: Backoff | None = None,
    ) -> None:
        self._retry_budget = retry_budget
        self._latency_budget = latency_budget
        self._backoff = backoff or NoBackoff()

    async def run(self, upstream: Upstream) -> Response:
        outcomes: list[Outcome] = []

        try:
            async with asyncio.timeout(self._latency_budget.total):
                while True:
                    outcome = await upstream.attempt(self._latency_budget.per_attempt)
                    outcomes.append(outcome)

                    if isinstance(outcome, Response) and outcome.ok:
                        return outcome

                    exhausted = self._retry_budget.exhausted_by(outcomes)

                    if exhausted is not None:
                        raise BudgetExhaustedError(exhausted, outcomes)

                    await asyncio.sleep(self._backoff.next_delay(outcomes))
        except TimeoutError:
            raise BudgetExhaustedError(Budget.LATENCY, outcomes) from None
