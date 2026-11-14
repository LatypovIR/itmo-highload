from resilience.models.client import ResilientClient
from resilience.models.endpoint import Endpoint
from resilience.models.outcome import Response
from resilience.models.strategy import ResilienceStrategy
from resilience.models.upstream import DirectUpstream


class StrategyClient(ResilientClient):
    def __init__(self, strategy: ResilienceStrategy) -> None:
        self._strategy = strategy

    async def execute(self, endpoint: Endpoint) -> Response:
        return await self._strategy.run(DirectUpstream(endpoint))
