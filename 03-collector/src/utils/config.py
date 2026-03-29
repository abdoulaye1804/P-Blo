"""Chargement de la configuration depuis les variables d'environnement."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    aws_region: str
    collect_interval: int   # secondes entre chaque cycle
    metrics_port: int       # port Prometheus

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            aws_region=os.getenv("AWS_REGION", "eu-west-1"),
            collect_interval=int(os.getenv("COLLECT_INTERVAL_SECONDS", "300")),
            metrics_port=int(os.getenv("METRICS_PORT", "8000")),
        )
