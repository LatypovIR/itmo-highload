import pytest

from fakes import HANG, FakeEndpoint
from resilience.clients.single import StrategyClient
from resilience.models.budget import Budget
from resilience.models.errors import BudgetExhaustedError
from resilience.models.outcome import Response
from resilience.strategies.default import DefaultStrategy


def make_client():
    return StrategyClient(DefaultStrategy(timeout=0.05))


async def test_returns_successful_response():
    endpoint = FakeEndpoint(200, body=b"payload")

    response = await make_client().execute(endpoint)

    assert response == Response(200, b"payload")


async def test_sends_only_one_subrequest():
    endpoint = FakeEndpoint(503)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client().execute(endpoint)

    assert error.value.budget is Budget.RETRIES
    assert endpoint.calls == 1


async def test_stops_waiting_after_timeout():
    endpoint = FakeEndpoint(HANG)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client().execute(endpoint)

    assert error.value.budget is Budget.LATENCY
    assert endpoint.cancelled == 1
