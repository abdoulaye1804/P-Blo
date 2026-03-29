import os
from dataclasses import dataclass


@dataclass
class Config:
    aws_region: str
    eval_interval: int
    policies_dir: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            aws_region=os.getenv("AWS_REGION", "eu-west-1"),
            eval_interval=int(os.getenv("EVAL_INTERVAL_SECONDS", "300")),
            policies_dir=os.getenv("POLICIES_DIR", "policies"),
        )
