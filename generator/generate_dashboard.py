"""Генератор дашборда — каркас.

Здесь уже есть только инфраструктурная часть: чтение токена service account
и проверка доступности Grafana и целевого приложения. Получение списка ручек,
построение дашборда через grafana-foundation-sdk и PromQL-запросы — ваша часть.
"""

import json
import os
import sys
import urllib.request

GRAFANA_URL = os.environ["GRAFANA_URL"].rstrip("/")
GRAFANA_TOKEN_FILE = os.environ["GRAFANA_TOKEN_FILE"]
TARGET_URL = os.environ["TARGET_URL"].rstrip("/")
DATASOURCE_UID = os.environ["DATASOURCE_UID"]


def read_token() -> str:
    with open(GRAFANA_TOKEN_FILE) as f:
        return f.read().strip()


def grafana_get(path: str, token: str):
    req = urllib.request.Request(GRAFANA_URL + path)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def check_target_health() -> None:
    with urllib.request.urlopen(f"{TARGET_URL}/health", timeout=5) as resp:
        print(f"target {TARGET_URL} is healthy: {resp.read().decode()}")


def main() -> int:
    token = read_token()
    datasource = grafana_get(f"/api/datasources/uid/{DATASOURCE_UID}", token)
    print(f"grafana auth ok, datasource '{datasource['name']}' found")
    check_target_health()
    # TODO(студент): получить список ручек у TARGET_URL, собрать дашборд через SDK
    # и отправить его в POST /api/dashboards/db (editable=false, overwrite=true).
    print("dashboard generation is not implemented yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
