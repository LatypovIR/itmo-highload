import asyncio
import contextlib

import pytest

from fakes import HANG, FakeEndpoint
from resilience.clients.circuit_breaker import CircuitBreakerConfig, CircuitBreakingMultiClient
from resilience.models.budget import LatencyBudget, RetryBudget
from resilience.models.errors import NoAvailableEndpointError, ResilienceError
from resilience.strategies.retry import RetryStrategy


def make_client():
    retry_budget = RetryBudget(max_retries=2, fast_errors=2, failures=2, timeouts=2)
    strategy = RetryStrategy(retry_budget, LatencyBudget(total=1.0, per_attempt=0.02))
    config = CircuitBreakerConfig(window_size=2, failure_rate_threshold=0.5, open_duration=0.2)

    return CircuitBreakingMultiClient(strategy, config)


async def send(client, *statuses):
    """Sends one request to fresh endpoints, returns how many subrequests each of them got."""
    endpoints = [FakeEndpoint(status) for status in statuses]

    with contextlib.suppress(ResilienceError):
        await client.execute(endpoints)

    return [endpoint.calls for endpoint in endpoints]


@pytest.mark.parametrize("error", [400, 503, HANG])
async def test_failing_endpoint_leaves_rotation(error):
    client = make_client()

    assert await send(client, error, 200) == [1, 1]
    assert await send(client, error, 200) == [1, 1]
    assert await send(client, error, 200) == [0, 1]


async def test_endpoint_returns_to_rotation_after_open_duration():
    client = make_client()
    await send(client, 503, 200)
    await send(client, 503, 200)

    await asyncio.sleep(0.25)

    assert await send(client, 503, 200) == [1, 1]
    assert await send(client, 200, 200) == [1, 0]


async def test_error_share_within_threshold_keeps_endpoint_in_rotation():
    client = make_client()
    await send(client, 503, 200)
    await send(client, 200, 200)

    assert await send(client, 200, 200) == [1, 0]


async def test_fails_fast_when_no_endpoint_is_available():
    client = make_client()
    await send(client, 503, 503)
    await send(client, 503, 503)
    endpoints = [FakeEndpoint(200), FakeEndpoint(200)]

    with pytest.raises(NoAvailableEndpointError):
        await client.execute(endpoints)

    assert [endpoint.calls for endpoint in endpoints] == [0, 0]
