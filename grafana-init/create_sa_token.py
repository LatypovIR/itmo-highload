"""Создаёт (идемпотентно) service account в Grafana и выпускает для него свежий токен.

Токен кладётся в файл на общем volume, а не в env/stdout, чтобы не светиться
в `docker inspect` и логах.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAFANA_URL = os.environ["GRAFANA_URL"].rstrip("/")
ADMIN_USER = os.environ["GRAFANA_ADMIN_USER"]
ADMIN_PASSWORD_FILE = os.environ["GRAFANA_ADMIN_PASSWORD_FILE"]
SA_NAME = os.environ["SA_NAME"]
SA_ROLE = os.environ.get("SA_ROLE", "Editor")
TOKEN_FILE = os.environ["TOKEN_FILE"]


def read_secret(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


def basic_auth_header() -> str:
    raw = f"{ADMIN_USER}:{read_secret(ADMIN_PASSWORD_FILE)}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(GRAFANA_URL + path, data=data, method=method)
    req.add_header("Authorization", basic_auth_header())
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = resp.read()
    return json.loads(payload) if payload else None


def find_or_create_service_account() -> int:
    query = urllib.parse.urlencode({"query": SA_NAME})
    found = call("GET", f"/api/serviceaccounts/search?{query}")
    for sa in found["serviceAccounts"]:
        if sa["name"] == SA_NAME:
            return sa["id"]
    created = call("POST", "/api/serviceaccounts", {"name": SA_NAME, "role": SA_ROLE})
    return created["id"]


def rotate_token(sa_id: int) -> str:
    # Старые токены отзываем, чтобы перезапуски compose не плодили живые ключи.
    for token in call("GET", f"/api/serviceaccounts/{sa_id}/tokens"):
        call("DELETE", f"/api/serviceaccounts/{sa_id}/tokens/{token['id']}")
    created = call("POST", f"/api/serviceaccounts/{sa_id}/tokens", {"name": f"{SA_NAME}-{int(time.time())}"})
    return created["key"]


def write_token(token: str) -> None:
    tmp_path = TOKEN_FILE + ".tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token)
    os.replace(tmp_path, TOKEN_FILE)


def main() -> None:
    sa_id = find_or_create_service_account()
    write_token(rotate_token(sa_id))
    print(f"service account '{SA_NAME}' (id={sa_id}): token written to {TOKEN_FILE}")


if __name__ == "__main__":
    main()
