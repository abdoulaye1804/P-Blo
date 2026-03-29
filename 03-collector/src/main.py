#!/usr/bin/env python3
"""
FinOps Autopilot — Collector
Point d'entrée principal. Lance la collecte périodique
des métriques cloud et Kubernetes.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime

from src.providers.aws import AWSProvider
from src.kubernetes.metrics import KubernetesMetricsCollector
from src.kubernetes.exporter import PrometheusExporter
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def collect_once(
    aws: AWSProvider,
    k8s: KubernetesMetricsCollector,
    exporter: PrometheusExporter,
) -> None:
    """Effectue un cycle complet de collecte."""
    logger.info("🔄 Début du cycle de collecte — %s", datetime.utcnow().isoformat())

    # Collecte AWS Cost Explorer
    try:
        costs = await aws.get_current_month_costs()
        idle_instances = await aws.get_idle_ec2_instances(cpu_threshold=10.0)
        unused_volumes = await aws.get_unused_volumes()

        exporter.update_aws_costs(costs)
        exporter.update_idle_instances(idle_instances)
        exporter.update_unused_volumes(unused_volumes)

        logger.info(
            "✅ AWS — coût mensuel: $%.2f | instances idle: %d | volumes inutilisés: %d",
            costs.get("total", 0),
            len(idle_instances),
            len(unused_volumes),
        )
    except Exception as e:
        logger.error("❌ Erreur collecte AWS: %s", e, exc_info=True)

    # Collecte métriques Kubernetes
    try:
        pods = await k8s.get_idle_pods(cpu_threshold=5.0, memory_threshold=10.0)
        nodes = await k8s.get_node_utilization()

        exporter.update_idle_pods(pods)
        exporter.update_node_utilization(nodes)

        logger.info(
            "✅ K8s — pods idle: %d | nodes collectés: %d",
            len(pods),
            len(nodes),
        )
    except Exception as e:
        logger.error("❌ Erreur collecte Kubernetes: %s", e, exc_info=True)

    logger.info("✅ Cycle de collecte terminé")


async def main() -> None:
    config = Config.from_env()
    logger.info("🚀 Collector démarré | intervalle: %ds", config.collect_interval)

    aws = AWSProvider(region=config.aws_region)
    k8s = KubernetesMetricsCollector()
    exporter = PrometheusExporter(port=config.metrics_port)

    exporter.start()
    logger.info("📡 Serveur Prometheus exposé sur :%d/metrics", config.metrics_port)

    # Gestion propre du SIGTERM (K8s graceful shutdown)
    shutdown_event = asyncio.Event()

    def handle_signal(*_):
        logger.info("🛑 Signal reçu — arrêt en cours...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while not shutdown_event.is_set():
        await collect_once(aws, k8s, exporter)
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=config.collect_interval,
            )
        except asyncio.TimeoutError:
            pass  # Timeout normal → nouveau cycle

    logger.info("👋 Collector arrêté proprement")


if __name__ == "__main__":
    asyncio.run(main())
