"""
Provider AWS — Cost Explorer + CloudWatch + EC2
Utilise boto3 avec les credentials IRSA injectés automatiquement par EKS.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class AWSProvider:
    """
    Collecte les données de coûts et d'utilisation AWS.

    Les credentials sont fournis automatiquement via IRSA
    (IAM Role for Service Accounts) — aucune clé en dur.
    """

    def __init__(self, region: str = "eu-west-1") -> None:
        self.region = region
        self._ce_client = None   # Cost Explorer (global, pas de région)
        self._cw_client = None   # CloudWatch
        self._ec2_client = None  # EC2

    # ── Clients lazy-init ──────────────────────────────────────────────────

    @property
    def ce(self):
        if not self._ce_client:
            # Cost Explorer est uniquement disponible en us-east-1
            self._ce_client = boto3.client("ce", region_name="us-east-1")
        return self._ce_client

    @property
    def cw(self):
        if not self._cw_client:
            self._cw_client = boto3.client("cloudwatch", region_name=self.region)
        return self._cw_client

    @property
    def ec2(self):
        if not self._ec2_client:
            self._ec2_client = boto3.client("ec2", region_name=self.region)
        return self._ec2_client

    # ── Cost Explorer ──────────────────────────────────────────────────────

    async def get_current_month_costs(self) -> dict[str, Any]:
        """
        Retourne les coûts du mois en cours, groupés par service AWS.
        """
        today = datetime.utcnow().date()
        start = today.replace(day=1).isoformat()
        end = today.isoformat()

        try:
            response = await asyncio.to_thread(
                self.ce.get_cost_and_usage,
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            results = response["ResultsByTime"]
            if not results:
                return {"total": 0.0, "by_service": {}}

            by_service = {}
            total = 0.0

            for group in results[0].get("Groups", []):
                service = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                by_service[service] = amount
                total += amount

            # Tri par coût décroissant
            by_service = dict(
                sorted(by_service.items(), key=lambda x: x[1], reverse=True)
            )

            return {
                "total": round(total, 4),
                "currency": "USD",
                "period": {"start": start, "end": end},
                "by_service": by_service,
            }

        except NoCredentialsError:
            logger.error("Pas de credentials AWS — vérifier l'annotation IRSA sur le ServiceAccount")
            raise
        except ClientError as e:
            logger.error("Erreur AWS Cost Explorer: %s", e.response["Error"]["Message"])
            raise

    async def get_daily_costs_last_30_days(self) -> list[dict]:
        """
        Retourne les coûts journaliers sur les 30 derniers jours.
        Utile pour détecter des anomalies de coût.
        """
        end = datetime.utcnow().date()
        start = end - timedelta(days=30)

        response = await asyncio.to_thread(
            self.ce.get_cost_and_usage,
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )

        daily = []
        for result in response["ResultsByTime"]:
            daily.append({
                "date": result["TimePeriod"]["Start"],
                "cost": round(float(result["Total"]["UnblendedCost"]["Amount"]), 4),
                "estimated": result.get("Estimated", False),
            })

        return daily

    # ── EC2 Idle Detection ─────────────────────────────────────────────────

    async def get_idle_ec2_instances(
        self,
        cpu_threshold: float = 10.0,
        lookback_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Retourne les instances EC2 dont le CPU moyen est
        inférieur à cpu_threshold % sur les dernières lookback_hours heures.
        """
        # Récupérer toutes les instances running
        response = await asyncio.to_thread(
            self.ec2.describe_instances,
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}],
        )

        instances = []
        for reservation in response["Reservations"]:
            for inst in reservation["Instances"]:
                instances.append({
                    "id": inst["InstanceId"],
                    "type": inst["InstanceType"],
                    "launch_time": inst["LaunchTime"].isoformat(),
                    "tags": {t["Key"]: t["Value"] for t in inst.get("Tags", [])},
                })

        if not instances:
            return []

        # Vérifier CPU de chaque instance via CloudWatch
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=lookback_hours)
        idle = []

        for inst in instances:
            avg_cpu = await self._get_ec2_avg_cpu(
                inst["id"], start_time, end_time
            )
            if avg_cpu is not None and avg_cpu < cpu_threshold:
                idle.append({
                    **inst,
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "lookback_hours": lookback_hours,
                    "recommendation": "downsize_or_stop",
                })

        logger.debug("Instances idle détectées: %d / %d", len(idle), len(instances))
        return idle

    async def _get_ec2_avg_cpu(
        self,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> float | None:
        """Retourne le CPU moyen d'une instance sur une période donnée."""
        try:
            response = await asyncio.to_thread(
                self.cw.get_metric_statistics,
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1h par datapoint
                Statistics=["Average"],
            )

            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return None

            return sum(d["Average"] for d in datapoints) / len(datapoints)

        except ClientError as e:
            logger.warning("Erreur CloudWatch pour %s: %s", instance_id, e)
            return None

    # ── EBS Volumes ────────────────────────────────────────────────────────

    async def get_unused_volumes(self) -> list[dict[str, Any]]:
        """
        Retourne les volumes EBS non attachés (state = available).
        Ce sont des coûts inutiles à supprimer ou snapshoter.
        """
        response = await asyncio.to_thread(
            self.ec2.describe_volumes,
            Filters=[{"Name": "status", "Values": ["available"]}],
        )

        volumes = []
        for vol in response["Volumes"]:
            volumes.append({
                "id": vol["VolumeId"],
                "size_gb": vol["Size"],
                "volume_type": vol["VolumeType"],
                "az": vol["AvailabilityZone"],
                "create_time": vol["CreateTime"].isoformat(),
                "tags": {t["Key"]: t["Value"] for t in vol.get("Tags", [])},
                "estimated_monthly_cost_usd": self._estimate_volume_cost(
                    vol["Size"], vol["VolumeType"]
                ),
                "recommendation": "snapshot_and_delete",
            })

        return volumes

    @staticmethod
    def _estimate_volume_cost(size_gb: int, volume_type: str) -> float:
        """Estimation du coût mensuel d'un volume EBS (prix eu-west-1)."""
        prices = {
            "gp2": 0.11,
            "gp3": 0.088,
            "io1": 0.138,
            "io2": 0.138,
            "st1": 0.05,
            "sc1": 0.028,
            "standard": 0.055,
        }
        price_per_gb = prices.get(volume_type, 0.10)
        return round(size_gb * price_per_gb, 2)
