#!/usr/bin/env python3
"""
FinOps Autopilot — Policy Engine
Évalue les politiques YAML et exécute les actions correctives.
"""

import asyncio
import logging
import signal
from datetime import datetime

from src.evaluator import PolicyEvaluator
from src.executor import PolicyExecutor
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def run_cycle(
    evaluator: PolicyEvaluator,
    executor: PolicyExecutor,
    resources: list[dict],
) -> None:
    """Un cycle complet : évaluation → exécution."""
    logger.info("🔄 Nouveau cycle — %s", datetime.utcnow().isoformat())

    # Rechargement des politiques à chaque cycle
    # (permet de modifier les YAML sans redémarrer)
    evaluator.load_policies()

    violations = evaluator.evaluate(resources)
    if not violations:
        logger.info("✅ Aucune violation détectée")
        return

    report = await executor.execute_violations(violations)

    savings = sum(
        action.get("result", {}).get("estimated_monthly_savings_usd", 0)
        for entry in report
        for action in entry.get("actions", [])
        if action.get("success")
    )
    logger.info(
        "📊 Cycle terminé — %d violation(s) traitée(s) | économies estimées: $%.2f/mois",
        len(report), savings,
    )


async def main() -> None:
    config = Config.from_env()
    logger.info("🚀 Policy Engine démarré | intervalle: %ds", config.eval_interval)

    evaluator = PolicyEvaluator(policies_dir=config.policies_dir)
    executor = PolicyExecutor(aws_region=config.aws_region)

    shutdown_event = asyncio.Event()

    def handle_signal(*_):
        logger.info("🛑 Arrêt en cours...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while not shutdown_event.is_set():
        # TODO Mois 2 : récupérer les ressources depuis une API interne
        # ou depuis un cache Redis partagé avec le Collector.
        # Pour l'instant : liste vide (mode développement)
        resources: list[dict] = []

        await run_cycle(evaluator, executor, resources)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=config.eval_interval)
        except asyncio.TimeoutError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
