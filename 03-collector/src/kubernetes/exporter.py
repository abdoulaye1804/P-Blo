"""
Exposition des métriques au format Prometheus.
Chaque métrique collectée devient un gauge consultable par Grafana.
"""

import logging
from prometheus_client import Gauge, start_http_server

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Expose les métriques FinOps au format Prometheus."""

    def __init__(self, port: int = 8000) -> None:
        self.port = port

        # ── Métriques AWS Cost Explorer ───────────────────────────────
        self.aws_monthly_cost = Gauge(
            "finops_aws_monthly_cost_usd",
            "Coût AWS du mois en cours en USD",
        )
        self.aws_service_cost = Gauge(
            "finops_aws_service_cost_usd",
            "Coût par service AWS en USD",
            ["service"],
        )
        self.aws_idle_instances_total = Gauge(
            "finops_aws_idle_ec2_instances_total",
            "Nombre d'instances EC2 idle (CPU < seuil)",
        )
        self.aws_idle_instance_cpu = Gauge(
            "finops_aws_idle_ec2_cpu_percent",
            "CPU moyen d'une instance EC2 idle",
            ["instance_id", "instance_type"],
        )
        self.aws_unused_volumes_total = Gauge(
            "finops_aws_unused_ebs_volumes_total",
            "Nombre de volumes EBS non attachés",
        )
        self.aws_unused_volumes_cost = Gauge(
            "finops_aws_unused_ebs_volumes_cost_usd",
            "Coût mensuel estimé des volumes EBS inutilisés",
        )

        # ── Métriques Kubernetes ──────────────────────────────────────
        self.k8s_idle_pods_total = Gauge(
            "finops_k8s_idle_pods_total",
            "Nombre de pods idle (CPU et mémoire sous les seuils)",
        )
        self.k8s_pod_cpu_usage = Gauge(
            "finops_k8s_pod_cpu_usage_percent",
            "Utilisation CPU d'un pod idle en %",
            ["namespace", "pod"],
        )
        self.k8s_node_cpu_usage = Gauge(
            "finops_k8s_node_cpu_usage_percent",
            "Utilisation CPU d'un node en %",
            ["node", "instance_type", "zone"],
        )
        self.k8s_node_mem_usage = Gauge(
            "finops_k8s_node_mem_usage_percent",
            "Utilisation mémoire d'un node en %",
            ["node", "instance_type", "zone"],
        )

    def start(self) -> None:
        start_http_server(self.port)
        logger.info("Serveur Prometheus démarré sur le port %d", self.port)

    # ── Mise à jour des métriques ─────────────────────────────────────────

    def update_aws_costs(self, costs: dict) -> None:
        self.aws_monthly_cost.set(costs.get("total", 0))
        for service, amount in costs.get("by_service", {}).items():
            self.aws_service_cost.labels(service=service).set(amount)

    def update_idle_instances(self, instances: list[dict]) -> None:
        self.aws_idle_instances_total.set(len(instances))
        for inst in instances:
            self.aws_idle_instance_cpu.labels(
                instance_id=inst["id"],
                instance_type=inst["type"],
            ).set(inst["avg_cpu_percent"])

    def update_unused_volumes(self, volumes: list[dict]) -> None:
        self.aws_unused_volumes_total.set(len(volumes))
        total_cost = sum(v.get("estimated_monthly_cost_usd", 0) for v in volumes)
        self.aws_unused_volumes_cost.set(total_cost)

    def update_idle_pods(self, pods: list[dict]) -> None:
        self.k8s_idle_pods_total.set(len(pods))
        for pod in pods:
            self.k8s_pod_cpu_usage.labels(
                namespace=pod["namespace"],
                pod=pod["name"],
            ).set(pod["cpu_usage_percent"])

    def update_node_utilization(self, nodes: list[dict]) -> None:
        for node in nodes:
            labels = {
                "node": node["name"],
                "instance_type": node.get("instance_type", "unknown"),
                "zone": node.get("zone", "unknown"),
            }
            self.k8s_node_cpu_usage.labels(**labels).set(node["cpu_usage_percent"])
            self.k8s_node_mem_usage.labels(**labels).set(node["mem_usage_percent"])
