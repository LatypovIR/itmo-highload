import time
from collections import defaultdict, deque
from dataclasses import dataclass

from resilience.clients.round_robin import EndpointHealth, RoundRobinMultiClient
from resilience.models.outcome import OutcomeKind
from resilience.models.strategy import ResilienceStrategy
from resilience.models.validation import require


@dataclass(frozen=True)
class CircuitBreakerConfig:
    window_size: int
    failure_rate_threshold: float
    open_duration: float

    def __post_init__(self) -> None:
        require(self.window_size >= 1, "window_size below 1")
        require(self.failure_rate_threshold >= 0, "negative failure_rate_threshold")
        require(self.failure_rate_threshold <= 1, "failure_rate_threshold above 1")
        require(self.open_duration > 0, "non-positive open_duration")


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._window: deque[bool] = deque(maxlen=config.window_size)
        self._open_until = 0.0

    def is_closed(self) -> bool:
        return time.monotonic() >= self._open_until

    def record(self, kind: OutcomeKind) -> None:
        if not self.is_closed():
            return

        self._window.append(kind is not OutcomeKind.SUCCESS)
        window_is_full = len(self._window) == self._config.window_size
        failure_rate = sum(self._window) / len(self._window)

        if window_is_full and failure_rate > self._config.failure_rate_threshold:
            self._open_until = time.monotonic() + self._config.open_duration
            self._window.clear()


class CircuitBreakers(EndpointHealth):
    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._breakers: dict[int, CircuitBreaker] = defaultdict(lambda: CircuitBreaker(config))

    def is_available(self, index: int) -> bool:
        return self._breakers[index].is_closed()

    def record(self, index: int, kind: OutcomeKind) -> None:
        self._breakers[index].record(kind)


class CircuitBreakingMultiClient(RoundRobinMultiClient):
    def __init__(self, strategy: ResilienceStrategy, config: CircuitBreakerConfig) -> None:
        super().__init__(strategy, CircuitBreakers(config))
