"""
Actions de remédiation — K8s Scale Down + EC2 Snapshot & Stop.
Toutes les actions destructives nécessitent dry_run=False explicite.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import boto3
from kubernetes import client, config

logger = logging.getLogger(__name__)


class ScaleDownAction:
    """Scale un Deployment Kubernetes à 0 réplicas."""

    def __init__(self, resource: dict, config: dict, dry_run: bool = True, **kwargs) -> None:
        self.resource = resource
        self.config = config
        self.dry_run = dry_run
        self._load_k8s()

    def _load_k8s(self) -> None:
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        self.apps_v1 = client.AppsV1Api()

    async def execute(self) -> dict[str, Any]:
        namespace = self.resource.get("namespace", "default")
        pod_name = self.resource.get("name", "")
        target_replicas = self.config.get("replicas", 0)

        # Trouver le Deployment parent du pod
        deployment_name = await self._find_parent_deployment(namespace, pod_name)
        if not deployment_name:
            raise RuntimeError(f"Aucun Deployment trouvé pour le pod {pod_name}")

        # Patch du Deployment
        patch = {"spec": {"replicas": target_replicas}}
        await asyncio.to_thread(
            self.apps_v1.patch_namespaced_deployment,
            name=deployment_name,
            namespace=namespace,
            body=patch,
        )

        logger.info(
            "📉 Deployment '%s/%s' scalé à %d réplica(s)",
            namespace, deployment_name, target_replicas,
        )
        return {
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas": target_replicas,
            "scaled_at": datetime.utcnow().isoformat(),
        }

    async def dry_run(self) -> dict[str, Any]:
        logger.info(
            "[DRY-RUN] Scale down du pod '%s/%s' à %d réplica(s)",
            self.resource.get("namespace"),
            self.resource.get("name"),
            self.config.get("replicas", 0),
        )
        return {"dry_run": True, "would_scale_to": self.config.get("replicas", 0)}

    async def _find_parent_deployment(
        self, namespace: str, pod_name: str
    ) -> str | None:
        """Remonte la chaîne OwnerReferences pour trouver le Deployment parent."""
        try:
            core_v1 = client.CoreV1Api()
            pod = await asyncio.to_thread(
                core_v1.read_namespaced_pod, name=pod_name, namespace=namespace
            )

            # Pod → ReplicaSet → Deployment
            for owner in pod.metadata.owner_references or []:
                if owner.kind == "ReplicaSet":
                    rs = await asyncio.to_thread(
                        self.apps_v1.read_namespaced_replica_set,
                        name=owner.name,
                        namespace=namespace,
                    )
                    for rs_owner in rs.metadata.owner_references or []:
                        if rs_owner.kind == "Deployment":
                            return rs_owner.name
        except Exception as e:
            logger.error("Erreur recherche Deployment parent: %s", e)
        return None


class SnapshotAndStopAction:
    """Crée un snapshot EBS puis arrête une instance EC2."""

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
        instance_id = self.resource["id"]
        snapshot_id = None

        # 1. Snapshot des volumes attachés
        if self.config.get("create_snapshot", True):
            snapshot_id = await self._snapshot_volumes(instance_id)

        # 2. Arrêt de l'instance
        await asyncio.to_thread(
            self.ec2.stop_instances,
            InstanceIds=[instance_id],
        )

        logger.info("🛑 Instance '%s' arrêtée | snapshot: %s", instance_id, snapshot_id)
        return {
            "instance_id": instance_id,
            "stopped": True,
            "snapshot_id": snapshot_id,
            "stopped_at": datetime.utcnow().isoformat(),
        }

    async def dry_run(self) -> dict[str, Any]:
        logger.info("[DRY-RUN] Stop instance '%s'", self.resource.get("id"))
        return {"dry_run": True, "instance_id": self.resource.get("id")}

    async def _snapshot_volumes(self, instance_id: str) -> str | None:
        """Crée un snapshot de tous les volumes attachés à l'instance."""
        try:
            response = await asyncio.to_thread(
                self.ec2.describe_instances,
                InstanceIds=[instance_id],
            )
            volumes = []
            for r in response["Reservations"]:
                for inst in r["Instances"]:
                    for mapping in inst.get("BlockDeviceMappings", []):
                        volumes.append(mapping["Ebs"]["VolumeId"])

            if volumes:
                snap = await asyncio.to_thread(
                    self.ec2.create_snapshot,
                    VolumeId=volumes[0],
                    Description=f"finops-autopilot | {instance_id} | {datetime.utcnow().date()}",
                    TagSpecifications=[{
                        "ResourceType": "snapshot",
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "finops-autopilot"},
                            {"Key": "SourceInstance", "Value": instance_id},
                        ],
                    }],
                )
                return snap["SnapshotId"]
        except Exception as e:
            logger.error("Erreur snapshot: %s", e)
        return None
