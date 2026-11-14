from abc import ABC, abstractmethod

from resilience.models.outcome import Response
from resilience.models.upstream import Upstream


class ResilienceStrategy(ABC):
    @abstractmethod
    async def run(self, upstream: Upstream) -> Response: ...
