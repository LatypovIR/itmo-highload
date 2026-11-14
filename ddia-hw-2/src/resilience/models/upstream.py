import asyncio
from abc import ABC, abstractmethod

from resilience.models.endpoint import Endpoint
from resilience.models.outcome import Outcome, TimedOut


class Upstream(ABC):
    @abstractmethod
    async def attempt(self, timeout: float) -> Outcome: ...


class DirectUpstream(Upstream):
    def __init__(self, endpoint: Endpoint) -> None:
        self._endpoint = endpoint

    async def attempt(self, timeout: float) -> Outcome:
        try:
            return await asyncio.wait_for(self._endpoint.send(), timeout)
        except TimeoutError:
            return TimedOut()
