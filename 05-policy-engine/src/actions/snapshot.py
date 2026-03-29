"""
Action SnapshotAndDelete — Snapshot puis suppression d'un volume EBS inutilisé.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class SnapshotAndDeleteAction:
    """Crée un snapshot d'un volume EBS puis le supprime."""

    def __init__(
        self,
        resource: dict,
        config: dict,
        dry_run: bool = True,
        aws_region: str = "eu-west-1",
        **kwargs,
    ) -> None:
        self.resource = resource
        self.config = config
        self.dry_run = dry_run
        self.ec2 = boto3.client("ec2", region_name=aws_region)

    async def execute(self) -> dict[str, Any]:
        volume_id = self.resource["id"]
        size_gb = self.resource.get("size_gb", 0)

        # 1. Snapshot du volume
        snap = await asyncio.to_thread(
            self.ec2.create_snapshot,
            VolumeId=volume_id,
            Description=f"finops-autopilot | pre-delete | {datetime.utcnow().date()}",
            TagSpecifications=[{
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": "ManagedBy", "Value": "finops-autopilot"},
                    {"Key": "SourceVolume", "Value": volume_id},
                    {"Key": "RetentionDays", "Value": str(self.config.get("snapshot_retention_days", 90))},
                ],
            }],
        )
        snapshot_id = snap["SnapshotId"]
        logger.info("📸 Snapshot créé : %s pour volume %s", snapshot_id, volume_id)

        # 2. Attendre que le snapshot soit disponible
        waiter = self.ec2.get_waiter("snapshot_completed")
        await asyncio.to_thread(waiter.wait, SnapshotIds=[snapshot_id])

        # 3. Suppression du volume
        await asyncio.to_thread(self.ec2.delete_volume, VolumeId=volume_id)
        logger.info(
            "🗑️  Volume '%s' (%d GB) supprimé | snapshot de sauvegarde : %s",
            volume_id, size_gb, snapshot_id,
        )

        return {
            "volume_id": volume_id,
            "size_gb": size_gb,
            "snapshot_id": snapshot_id,
            "deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "estimated_monthly_savings_usd": self.resource.get("estimated_monthly_cost_usd", 0),
        }

    async def dry_run(self) -> dict[str, Any]:
        logger.info(
            "[DRY-RUN] Snapshot + suppression volume '%s' (%d GB) — économie estimée: $%.2f/mois",
            self.resource.get("id"),
            self.resource.get("size_gb", 0),
            self.resource.get("estimated_monthly_cost_usd", 0),
        )
        return {
            "dry_run": True,
            "volume_id": self.resource.get("id"),
            "would_save_usd": self.resource.get("estimated_monthly_cost_usd", 0),
        }
