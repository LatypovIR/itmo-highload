import asyncio
import time

from resilience.models.endpoint import Endpoint
from resilience.models.outcome import Response

HANG = None


class FakeEndpoint(Endpoint):
    """Replies with the given statuses in order, the last one repeats. HANG never replies."""

    def __init__(self, *statuses, latency=0.0, body=b""):
        self._statuses = list(statuses)
        self._latency = latency
        self._body = body
        self.sent_at = []
        self.cancelled = 0

    @property
    def calls(self):
        return len(self.sent_at)

    async def send(self):
        self.sent_at.append(time.monotonic())
        status = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]

        try:
            await asyncio.sleep(3600 if status is HANG else self._latency)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise

        return Response(status, self._body)
