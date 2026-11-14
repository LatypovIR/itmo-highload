from abc import ABC, abstractmethod
from collections.abc import Sequence

from resilience.models.endpoint import Endpoint
from resilience.models.outcome import Response


class ResilientClient(ABC):
    @abstractmethod
    async def execute(self, endpoint: Endpoint) -> Response: ...


class ResilientMultiClient(ABC):
    @abstractmethod
    async def execute(self, endpoints: Sequence[Endpoint]) -> Response: ...
