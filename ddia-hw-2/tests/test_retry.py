import pytest

from fakes import HANG, FakeEndpoint
from resilience.clients.single import StrategyClient
from resilience.models.budget import Budget, LatencyBudget, RetryBudget
from resilience.models.errors import BudgetExhaustedError
from resilience.strategies.retry import RetryStrategy


def make_client(retry_budget, total=1.0):
    latency_budget = LatencyBudget(total=total, per_attempt=0.05)

    return StrategyClient(RetryStrategy(retry_budget, latency_budget))


async def test_retries_until_success():
    endpoint = FakeEndpoint(400, 503, HANG, 200)
    retry_budget = RetryBudget(max_retries=4, fast_errors=2, failures=2, timeouts=2)

    response = await make_client(retry_budget).execute(endpoint)

    assert response.status == 200
    assert endpoint.calls == 4


@pytest.mark.parametrize(
    ("status", "retry_budget", "exhausted"),
    [
        (400, RetryBudget(max_retries=10, fast_errors=3), Budget.FAST_ERRORS),
        (503, RetryBudget(max_retries=10, failures=3), Budget.FAILURES),
        (HANG, RetryBudget(max_retries=10, timeouts=3), Budget.TIMEOUTS),
    ],
)
async def test_error_budget_ends_request(status, retry_budget, exhausted):
    endpoint = FakeEndpoint(status)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client(retry_budget).execute(endpoint)

    assert error.value.budget is exhausted
    assert endpoint.calls == 3


async def test_max_retries_limits_subrequests():
    endpoint = FakeEndpoint(503)
    retry_budget = RetryBudget(max_retries=3, failures=10)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client(retry_budget).execute(endpoint)

    assert error.value.budget is Budget.RETRIES
    assert endpoint.calls == 3


async def test_latency_budget_ends_request():
    endpoint = FakeEndpoint(503, latency=0.02)
    retry_budget = RetryBudget(max_retries=100, failures=100, timeouts=100)

    with pytest.raises(BudgetExhaustedError) as error:
        await make_client(retry_budget, total=0.1).execute(endpoint)

    assert error.value.budget is Budget.LATENCY
