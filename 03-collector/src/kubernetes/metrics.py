"""
Collecteur de métriques Kubernetes.
Utilise l'API K8s + Metrics Server pour détecter les pods idle.
"""

import logging
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesMetricsCollector:
    """
    Collecte les métriques des pods et nodes via l'API Kubernetes.
    Se connecte automatiquement (in-cluster en prod, kubeconfig en local).
    """

    def __init__(self) -> None:
        self._load_config()
        self.core_v1 = client.CoreV1Api()
        self.custom = client.CustomObjectsApi()

    def _load_config(self) -> None:
        """Charge la config K8s — in-cluster ou kubeconfig local."""
        try:
            config.load_incluster_config()
            logger.info("Config K8s chargée (in-cluster)")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Config K8s chargée (kubeconfig local)")

    # ── Pods ───────────────────────────────────────────────────────────────

    async def get_idle_pods(
        self,
        cpu_threshold: float = 5.0,
        memory_threshold: float = 10.0,
        exclude_namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retourne les pods dont CPU et mémoire sont sous les seuils.
        Exclut les namespaces système par défaut.
        """
        if exclude_namespaces is None:
            exclude_namespaces = ["kube-system", "kube-public", "kube-node-lease"]

        try:
            # Métriques via Metrics Server (CustomObjectsApi)
            metrics_response = self.custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods",
            )
        except ApiException as e:
            logger.error("Metrics Server non disponible: %s", e)
            return []

        # Récupérer les limites/requests des pods
        pods_info = await self._get_pods_resources(exclude_namespaces)

        idle_pods = []
        for pod_metric in metrics_response.get("items", []):
            namespace = pod_metric["metadata"]["namespace"]
            name = pod_metric["metadata"]["name"]

            if namespace in exclude_namespaces:
                continue

            # Calcul CPU et mémoire utilisés
            cpu_usage = self._sum_container_cpu(pod_metric["containers"])
            mem_usage = self._sum_container_memory(pod_metric["containers"])

            pod_key = f"{namespace}/{name}"
            pod_info = pods_info.get(pod_key, {})
            cpu_request = pod_info.get("cpu_request_millicores", 0)
            mem_request = pod_info.get("mem_request_mib", 0)

            # Calcul du pourcentage d'utilisation vs request
            cpu_pct = (cpu_usage / cpu_request * 100) if cpu_request > 0 else 0
            mem_pct = (mem_usage / mem_request * 100) if mem_request > 0 else 0

            if cpu_pct < cpu_threshold and mem_pct < memory_threshold:
                idle_pods.append({
                    "namespace": namespace,
                    "name": name,
                    "cpu_usage_millicores": cpu_usage,
                    "cpu_request_millicores": cpu_request,
                    "cpu_usage_percent": round(cpu_pct, 2),
                    "mem_usage_mib": mem_usage,
                    "mem_request_mib": mem_request,
                    "mem_usage_percent": round(mem_pct, 2),
                    "node": pod_info.get("node", "unknown"),
                    "recommendation": "scale_down_or_delete",
                })

        return idle_pods

    async def _get_pods_resources(
        self, exclude_namespaces: list[str]
    ) -> dict[str, dict]:
        """Retourne les resources requests de tous les pods."""
        pods_info = {}
        try:
            pods = self.core_v1.list_pod_for_all_namespaces(watch=False)
            for pod in pods.items:
                if pod.metadata.namespace in exclude_namespaces:
                    continue

                cpu_req = 0
                mem_req = 0
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        cpu_req += self._parse_cpu(
                            container.resources.requests.get("cpu", "0")
                        )
                        mem_req += self._parse_memory(
                            container.resources.requests.get("memory", "0")
                        )

                key = f"{pod.metadata.namespace}/{pod.metadata.name}"
                pods_info[key] = {
                    "cpu_request_millicores": cpu_req,
                    "mem_request_mib": mem_req,
                    "node": pod.spec.node_name or "unknown",
                }
        except ApiException as e:
            logger.error("Erreur listing pods: %s", e)

        return pods_info

    # ── Nodes ──────────────────────────────────────────────────────────────

    async def get_node_utilization(self) -> list[dict[str, Any]]:
        """Retourne l'utilisation CPU/mémoire de chaque node."""
        try:
            node_metrics = self.custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
            )
            nodes_api = self.core_v1.list_node()
        except ApiException as e:
            logger.error("Erreur métriques nodes: %s", e)
            return []

        # Map capacité des nodes
        capacity_map = {}
        for node in nodes_api.items:
            name = node.metadata.name
            capacity_map[name] = {
                "cpu_millicores": self._parse_cpu(node.status.capacity.get("cpu", "0")),
                "mem_mib": self._parse_memory(node.status.capacity.get("memory", "0")),
                "instance_type": node.metadata.labels.get(
                    "node.kubernetes.io/instance-type", "unknown"
                ),
                "zone": node.metadata.labels.get(
                    "topology.kubernetes.io/zone", "unknown"
                ),
            }

        utilization = []
        for node_metric in node_metrics.get("items", []):
            name = node_metric["metadata"]["name"]
            cpu_used = self._parse_cpu(node_metric["usage"]["cpu"])
            mem_used = self._parse_memory(node_metric["usage"]["memory"])
            cap = capacity_map.get(name, {})

            cpu_cap = cap.get("cpu_millicores", 1)
            mem_cap = cap.get("mem_mib", 1)

            utilization.append({
                "name": name,
                "instance_type": cap.get("instance_type"),
                "zone": cap.get("zone"),
                "cpu_used_millicores": cpu_used,
                "cpu_capacity_millicores": cpu_cap,
                "cpu_usage_percent": round(cpu_used / cpu_cap * 100, 2),
                "mem_used_mib": mem_used,
                "mem_capacity_mib": mem_cap,
                "mem_usage_percent": round(mem_used / mem_cap * 100, 2),
            })

        return utilization

    # ── Helpers de parsing ─────────────────────────────────────────────────

    @staticmethod
    def _parse_cpu(cpu_str: str) -> int:
        """Convertit '250m', '1', '2' en millicores."""
        if not cpu_str or cpu_str == "0":
            return 0
        if cpu_str.endswith("m"):
            return int(cpu_str[:-1])
        return int(float(cpu_str) * 1000)

    @staticmethod
    def _parse_memory(mem_str: str) -> int:
        """Convertit '256Mi', '1Gi', '512Ki' en MiB."""
        if not mem_str or mem_str == "0":
            return 0
        units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024}
        for unit, factor in units.items():
            if mem_str.endswith(unit):
                return int(float(mem_str[: -len(unit)]) * factor)
        return int(mem_str) // (1024 * 1024)  # bytes → MiB

    @staticmethod
    def _sum_container_cpu(containers: list[dict]) -> int:
        total = 0
        for c in containers:
            cpu = c.get("usage", {}).get("cpu", "0")
            if cpu.endswith("n"):  # nanocores
                total += int(cpu[:-1]) // 1_000_000
            elif cpu.endswith("m"):
                total += int(cpu[:-1])
            else:
                total += int(float(cpu) * 1000)
        return total

    @staticmethod
    def _sum_container_memory(containers: list[dict]) -> int:
        total = 0
        for c in containers:
            mem = c.get("usage", {}).get("memory", "0")
            if mem.endswith("Ki"):
                total += int(mem[:-2]) // 1024
            elif mem.endswith("Mi"):
                total += int(mem[:-2])
            elif mem.endswith("Gi"):
                total += int(mem[:-2]) * 1024
        return total
