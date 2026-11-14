import pytest

from fakes import HANG, FakeEndpoint
from resilience.clients.hedging import HedgingMultiClient
from resilience.models.budget import Budget
from resilience.models.errors import BudgetExhaustedError
from resilience.models.outcome import Response
from resilience.strategies.default import DefaultStrategy


def make_client(latency_budget=1.0):
    strategy = DefaultStrategy(timeout=1.0)

    return HedgingMultiClient(strategy, hedging_delay=0.05, latency_budget=latency_budget)


async def test_fast_first_endpoint_is_not_hedged():
    first, second = FakeEndpoint(200, latency=0.02), FakeEndpoint(200)

    response = await make_client().execute([first, second])

    assert response.status == 200
    assert (first.calls, second.calls) == (1, 0)


async def test_slow_first_endpoint_is_hedged_to_all_others():
    slow = FakeEndpoint(200, latency=0.5, body=b"slow")
    hanging = FakeEndpoint(HANG)
    fast = FakeEndpoint(200, body=b"fast")

    response = await make_client().execute([slow, hanging, fast])

    assert response.body == b"fast"
    assert (hanging.calls, fast.calls) == (1, 1)
    assert (slow.cancelled, hanging.cancelled) == (1, 1)


async def test_fails_when_every_endpoint_fails():
    first, second = FakeEndpoint(503), FakeEndpoint(400)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client().execute([first, second])

    assert error.value.budget is Budget.RETRIES
    assert error.value.outcomes == (Response(503), Response(400))


async def test_latency_budget_ends_request():
    first, second = FakeEndpoint(HANG), FakeEndpoint(HANG)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client(latency_budget=0.1).execute([first, second])

    assert error.value.budget is Budget.LATENCY
    assert (first.cancelled, second.cancelled) == (1, 1)
