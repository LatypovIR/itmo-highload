import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    pod_id: str
    datacenter: str
    deployment_name: str
    fault_rate: float


def load_settings() -> Settings:
    return Settings(
        pod_id=os.environ["POD_ID"],
        datacenter=os.environ["DATACENTER"],
        deployment_name=os.environ["DEPLOYMENT_NAME"],
        fault_rate=float(os.environ.get("FAULT_RATE", "0")),
    )
