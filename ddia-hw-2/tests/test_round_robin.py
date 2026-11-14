import pytest

from fakes import FakeEndpoint
from resilience.clients.round_robin import RoundRobinMultiClient
from resilience.models.budget import Budget, LatencyBudget, RetryBudget
from resilience.models.errors import BudgetExhaustedError
from resilience.strategies.backoff import ExponentialBackoff
from resilience.strategies.retry import RetryStrategy


def make_client(backoff=None):
    retry_budget = RetryBudget(max_retries=4, failures=4)

    return RoundRobinMultiClient(RetryStrategy(retry_budget, LatencyBudget(total=1.0), backoff))


async def test_next_subrequest_goes_to_next_endpoint():
    first, second, third = FakeEndpoint(503), FakeEndpoint(200), FakeEndpoint(200)

    response = await make_client().execute([first, second, third])

    assert response.status == 200
    assert (first.calls, second.calls, third.calls) == (1, 1, 0)


async def test_rotation_wraps_around():
    first, second, third = FakeEndpoint(503, 200), FakeEndpoint(503), FakeEndpoint(503)

    response = await make_client().execute([first, second, third])

    assert response.status == 200
    assert (first.calls, second.calls, third.calls) == (2, 1, 1)


async def test_retry_budget_is_shared_by_endpoints():
    first, second = FakeEndpoint(503), FakeEndpoint(503)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client().execute([first, second])

    assert error.value.budget is Budget.FAILURES
    assert (first.calls, second.calls) == (2, 2)


async def test_exponential_backoff_works_as_subrequest_strategy():
    first, second = FakeEndpoint(503), FakeEndpoint(200)
    client = make_client(ExponentialBackoff(initial_delay=0.05))

    response = await client.execute([first, second])

    assert response.status == 200
    # the delay is 0.05, the margin covers timer precision
    assert second.sent_at[0] - first.sent_at[0] >= 0.04
