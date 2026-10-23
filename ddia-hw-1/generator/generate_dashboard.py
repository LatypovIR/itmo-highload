import json
import os
import urllib.request

from grafana_foundation_sdk.builders import dashboard, prometheus, timeseries
from grafana_foundation_sdk.cog.encoder import JSONEncoder
from grafana_foundation_sdk.models.dashboard import DataSourceRef, VariableRefresh

GRAFANA_URL = "http://grafana:3000"
TOKEN_FILE = "/run/grafana-sa/token"
DATASOURCE = DataSourceRef(type_val="prometheus", uid="victoriametrics")
PERCENTILES = (50, 75, 90, 95, 99)


def panel(title: str, unit: str, queries: dict[str, str]) -> timeseries.Panel:
    result = timeseries.Panel().title(title).unit(unit).span(8).datasource(DATASOURCE)
    for legend, expr in queries.items():
        result.with_target(prometheus.Dataquery().expr(expr).legend_format(legend))
    return result


def handler_panels(deployment: str, handler: str) -> list[timeseries.Panel]:
    labels = f'{{deployment="{deployment}", datacenter=~"$datacenter", pod=~"$pod", handler="{handler}"}}'
    requests = f"rate(http_requests_total{labels}[$__rate_interval])"
    buckets = f"sum by (le) (rate(http_request_duration_seconds_bucket{labels}[$__rate_interval]))"
    errors = f"sum by (status_code) (rate(http_errors_total{labels}[$__rate_interval]))"
    return [
        panel("RPS", "reqps", {"total": f"sum({requests})", "{{datacenter}}": f"sum by (datacenter) ({requests})"}),
        panel("Latency", "s", {f"p{p}": f"histogram_quantile({p / 100}, {buckets})" for p in PERCENTILES}),
        panel("Errors by status code", "reqps", {"{{status_code}}": errors}),
    ]


def label_variable(name: str, labels: str) -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable(name)
        .datasource(DATASOURCE)
        .query(f"label_values(http_requests_total{labels}, {name})")
        .refresh(VariableRefresh.ON_TIME_RANGE_CHANGED)
        .multi(True)
        .include_all(True)
    )


def build_dashboard(deployment: str, handlers: list[str]) -> dashboard.Dashboard:
    builder = (
        dashboard.Dashboard(f"{deployment}: golden signals")
        .uid(deployment)
        .readonly()
        .time("now-15m", "now")
        .refresh("10s")
        .with_variable(label_variable("datacenter", f'{{deployment="{deployment}"}}'))
        .with_variable(label_variable("pod", f'{{deployment="{deployment}", datacenter=~"$datacenter"}}'))
    )
    for handler in handlers:
        builder.with_row(dashboard.Row(handler))
        for handler_panel in handler_panels(deployment, handler):
            builder.with_panel(handler_panel)
    return builder


def main() -> None:
    with urllib.request.urlopen(f"{os.environ['TARGET_URL']}/endpoints") as resp:
        discovered = json.load(resp)
    print(f"handlers of {discovered['deployment']}: {discovered['handlers']}")

    with open(TOKEN_FILE) as f:
        token = f.read()
    body = json.dumps({"dashboard": build_dashboard(**discovered).build(), "overwrite": True}, cls=JSONEncoder)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    request = urllib.request.Request(f"{GRAFANA_URL}/api/dashboards/db", body.encode(), headers)
    with urllib.request.urlopen(request) as resp:
        print(f"dashboard saved: {GRAFANA_URL}{json.load(resp)['url']}")


if __name__ == "__main__":
    main()
