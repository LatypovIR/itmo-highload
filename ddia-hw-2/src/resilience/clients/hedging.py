import asyncio
from collections.abc import Sequence

from resilience.models.budget import Budget
from resilience.models.client import ResilientMultiClient
from resilience.models.endpoint import Endpoint
from resilience.models.errors import BudgetExhaustedError
from resilience.models.outcome import Outcome, Response
from resilience.models.strategy import ResilienceStrategy
from resilience.models.upstream import DirectUpstream
from resilience.models.validation import require


class HedgingMultiClient(ResilientMultiClient):
    def __init__(
        self,
        subrequest_strategy: ResilienceStrategy,
        hedging_delay: float,
        latency_budget: float,
    ) -> None:
        require(hedging_delay >= 0, "negative hedging_delay")
        require(latency_budget > 0, "non-positive latency_budget")
        self._subrequest_strategy = subrequest_strategy
        self._hedging_delay = hedging_delay
        self._latency_budget = latency_budget

    async def execute(self, endpoints: Sequence[Endpoint]) -> Response:
        first, *others = endpoints
        subrequests = [self._send(first)]
        failures: list[Outcome] = []

        try:
            async with asyncio.timeout(self._latency_budget):
                await asyncio.wait(subrequests, timeout=self._hedging_delay)
                answered = subrequests[0].done() and subrequests[0].exception() is None

                if not answered:
                    subrequests += [self._send(endpoint) for endpoint in others]

                for completed in asyncio.as_completed(subrequests):
                    try:
                        return await completed
                    except BudgetExhaustedError as error:
                        failures += error.outcomes

                raise BudgetExhaustedError(Budget.RETRIES, failures)
        except TimeoutError:
            raise BudgetExhaustedError(Budget.LATENCY, failures) from None
        finally:
            for subrequest in subrequests:
                subrequest.cancel()

            await asyncio.gather(*subrequests, return_exceptions=True)

    def _send(self, endpoint: Endpoint) -> asyncio.Task[Response]:
        return asyncio.create_task(self._subrequest_strategy.run(DirectUpstream(endpoint)))
