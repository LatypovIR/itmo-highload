import base64
import json
import os
import urllib.request

GRAFANA_URL = "http://grafana:3000"
SA_NAME = "dashboard-generator"
TOKEN_FILE = "/run/grafana-sa/token"

def read_credentials() -> str:
    with open("/run/secrets/grafana_admin_password") as f:
        return base64.b64encode(f"admin:{f.read().strip()}".encode()).decode()


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Basic {read_credentials()}", "Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(GRAFANA_URL + path, data, headers, method=method)) as resp:
        return json.load(resp)


def main() -> None:
    found = call("GET", f"/api/serviceaccounts/search?query={SA_NAME}")["serviceAccounts"]
    account_id = found[0]["id"] if found else call("POST", "/api/serviceaccounts", {"name": SA_NAME, "role": "Editor"})["id"]
    for stale in call("GET", f"/api/serviceaccounts/{account_id}/tokens"):
        call("DELETE", f"/api/serviceaccounts/{account_id}/tokens/{stale['id']}")
    token = call("POST", f"/api/serviceaccounts/{account_id}/tokens", {"name": SA_NAME})["key"]

    with os.fdopen(os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        f.write(token)
    print(f"service account '{SA_NAME}': token written to {TOKEN_FILE}")


if __name__ == "__main__":
    main()
