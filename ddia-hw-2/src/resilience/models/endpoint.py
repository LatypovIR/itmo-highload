from abc import ABC, abstractmethod

from resilience.models.outcome import Response


class Endpoint(ABC):
    @abstractmethod
    async def send(self) -> Response: ...
