"""
Executor — déclenche les actions définies dans les politiques.
Supporte : notify, scale_down, snapshot_and_stop, snapshot_and_delete.
Chaque action avec require_approval=true passe par le Slack bot.
"""

import logging
from typing import Any

from src.actions.notify import NotifyAction
from src.actions.resize import ScaleDownAction, SnapshotAndStopAction
from src.actions.snapshot import SnapshotAndDeleteAction

logger = logging.getLogger(__name__)

# Registre des actions disponibles
ACTION_REGISTRY = {
    "notify":               NotifyAction,
    "scale_down":           ScaleDownAction,
    "snapshot_and_stop":    SnapshotAndStopAction,
    "snapshot_and_delete":  SnapshotAndDeleteAction,
}


class PolicyExecutor:
    """
    Reçoit la liste des violations et exécute les actions associées.
    Respecte dry_run et require_approval pour chaque action.
    """

    def __init__(self, aws_region: str = "eu-west-1") -> None:
        self.aws_region = aws_region

    async def execute_violations(
        self, violations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Exécute les actions pour chaque violation.
        Retourne un rapport d'exécution.
        """
        report = []

        for violation in violations:
            policy_name = violation["policy"]
            resource = violation["resource"]
            resource_id = resource.get("id") or resource.get("name", "unknown")

            logger.info("⚡ Traitement violation '%s' sur '%s'", policy_name, resource_id)

            action_results = []
            for action_def in violation["actions"]:
                result = await self._execute_action(action_def, resource, violation)
                action_results.append(result)

                # Si une action bloquante échoue → on arrête la chaîne
                if not result["success"] and not action_def.get("config", {}).get("continue_on_failure"):
                    logger.warning(
                        "Action '%s' échouée — chaîne interrompue pour '%s'",
                        action_def["type"], resource_id,
                    )
                    break

            report.append({
                "policy": policy_name,
                "resource_id": resource_id,
                "resource_type": resource.get("resource_type"),
                "actions": action_results,
            })

        return report

    async def _execute_action(
        self,
        action_def: dict,
        resource: dict,
        violation: dict,
    ) -> dict[str, Any]:
        """Instancie et exécute une action individuelle."""
        action_type = action_def["type"]
        config = action_def.get("config", {})
        dry_run = action_def.get("dry_run", True)  # Sécurité : dry_run par défaut

        action_class = ACTION_REGISTRY.get(action_type)
        if not action_class:
            logger.error("Action inconnue : '%s'", action_type)
            return {"type": action_type, "success": False, "error": "Action inconnue"}

        action = action_class(
            resource=resource,
            config=config,
            dry_run=dry_run,
            aws_region=self.aws_region,
        )

        try:
            if dry_run:
                logger.info(
                    "🔍 [DRY-RUN] Action '%s' sur '%s' — aucune modification réelle",
                    action_type,
                    resource.get("id") or resource.get("name"),
                )
                result = await action.dry_run()
            else:
                result = await action.execute()

            return {
                "type": action_type,
                "success": True,
                "dry_run": dry_run,
                "result": result,
            }

        except Exception as e:
            logger.error(
                "❌ Erreur action '%s' sur '%s': %s",
                action_type,
                resource.get("id", "?"),
                e,
                exc_info=True,
            )
            return {
                "type": action_type,
                "success": False,
                "dry_run": dry_run,
                "error": str(e),
            }
