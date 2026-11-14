from fakes import FakeEndpoint
from resilience.clients.single import StrategyClient
from resilience.models.budget import LatencyBudget, RetryBudget
from resilience.models.outcome import Response, TimedOut
from resilience.strategies.backoff import ExponentialBackoff
from resilience.strategies.retry import RetryStrategy


def test_delay_doubles_after_server_errors_and_timeouts():
    backoff = ExponentialBackoff(initial_delay=1.0)

    assert backoff.next_delay([Response(503)]) == 1.0
    assert backoff.next_delay([Response(503), TimedOut()]) == 2.0
    assert backoff.next_delay([Response(503), TimedOut(), Response(503)]) == 4.0


def test_no_delay_after_client_error():
    backoff = ExponentialBackoff(initial_delay=1.0)

    assert backoff.next_delay([Response(503), Response(400)]) == 0.0


def test_delay_is_limited_by_max_delay():
    backoff = ExponentialBackoff(initial_delay=1.0, max_delay=3.0)

    assert backoff.next_delay([Response(503)] * 3) == 3.0


async def test_strategy_waits_between_retries():
    endpoint = FakeEndpoint(503, 503, 200)
    strategy = RetryStrategy(
        RetryBudget(max_retries=3, failures=3),
        LatencyBudget(total=1.0),
        ExponentialBackoff(initial_delay=0.05),
    )

    await StrategyClient(strategy).execute(endpoint)

    first, second, third = endpoint.sent_at
    # delays are 0.05 and 0.1, the margin covers timer precision
    assert second - first >= 0.04
    assert third - second >= 0.09
