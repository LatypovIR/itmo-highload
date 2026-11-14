import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence

from resilience.models.client import ResilientMultiClient
from resilience.models.endpoint import Endpoint
from resilience.models.errors import NoAvailableEndpointError
from resilience.models.outcome import Outcome, OutcomeKind, Response
from resilience.models.strategy import ResilienceStrategy
from resilience.models.upstream import DirectUpstream, Upstream


class EndpointHealth(ABC):
    @abstractmethod
    def is_available(self, index: int) -> bool: ...

    @abstractmethod
    def record(self, index: int, kind: OutcomeKind) -> None: ...


class AlwaysAvailable(EndpointHealth):
    def is_available(self, index: int) -> bool:
        return True

    def record(self, index: int, kind: OutcomeKind) -> None:
        pass


class RoundRobinUpstream(Upstream):
    def __init__(self, endpoints: Sequence[Endpoint], health: EndpointHealth) -> None:
        self._upstreams = [DirectUpstream(endpoint) for endpoint in endpoints]
        self._health = health
        self._next_index = 0

    async def attempt(self, timeout: float) -> Outcome:
        index = self._select()

        try:
            outcome = await self._upstreams[index].attempt(timeout)
        except asyncio.CancelledError:
            self._health.record(index, OutcomeKind.TIMEOUT)
            raise

        self._health.record(index, outcome.kind)

        return outcome

    def _select(self) -> int:
        count = len(self._upstreams)

        for offset in range(count):
            index = (self._next_index + offset) % count

            if self._health.is_available(index):
                self._next_index = index + 1

                return index

        raise NoAvailableEndpointError


class RoundRobinMultiClient(ResilientMultiClient):
    def __init__(self, strategy: ResilienceStrategy, health: EndpointHealth | None = None) -> None:
        self._strategy = strategy
        self._health = health or AlwaysAvailable()

    async def execute(self, endpoints: Sequence[Endpoint]) -> Response:
        return await self._strategy.run(RoundRobinUpstream(endpoints, self._health))
