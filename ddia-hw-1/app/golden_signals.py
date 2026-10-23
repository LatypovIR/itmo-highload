import os
import time

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match

LABELS = ("deployment", "datacenter", "pod", "handler", "metric_type")
LATENCY_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)

LATENCY = Histogram("http_request_duration_seconds", "Handler latency", LABELS, buckets=LATENCY_BUCKETS)
REQUESTS = Counter("http_requests", "Handled requests", (*LABELS, "status_code"))
ERRORS = Counter("http_errors", "Requests answered with 4xx/5xx", (*LABELS, "status_code"))


def instrumented_routes(app: FastAPI) -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute) and route.include_in_schema]


def resolve_handler(app: FastAPI, request: Request) -> str | None:
    for route in instrumented_routes(app):
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return f"{request.method} {route.path}"
    return None


def instrument(app: FastAPI) -> None:
    pod = {
        "deployment": os.environ["DEPLOYMENT_NAME"],
        "datacenter": os.environ["DATACENTER"],
        "pod": os.environ["POD_ID"],
    }

    def observe(handler: str, status_code: int, seconds: float) -> None:
        labels = {**pod, "handler": handler}
        LATENCY.labels(**labels, metric_type="latency").observe(seconds)
        REQUESTS.labels(**labels, metric_type="traffic", status_code=status_code).inc()
        if status_code >= 400:
            ERRORS.labels(**labels, metric_type="errors", status_code=status_code).inc()

    @app.middleware("http")
    async def golden_signals(request: Request, call_next) -> Response:
        handler = resolve_handler(app, request)
        if handler is None:
            return await call_next(request)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            observe(handler, status_code, time.perf_counter() - started)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/endpoints", include_in_schema=False)
    async def endpoints() -> dict:
        handlers = [f"{method} {route.path}" for route in instrumented_routes(app) for method in route.methods]
        return {"deployment": pod["deployment"], "handlers": handlers}
