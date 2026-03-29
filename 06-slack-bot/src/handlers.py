"""
Handlers des boutons Approve / Reject.
Quand un utilisateur clique sur Approuver → l'action est exécutée.
Quand il clique sur Rejeter → l'action est annulée et loggée.
"""

import json
import logging
import os
from datetime import datetime

import aiohttp
import boto3

logger = logging.getLogger(__name__)

# Store en mémoire des actions en attente d'approbation
# En prod : remplacer par Redis pour la persistance multi-pods
PENDING_ACTIONS: dict[str, dict] = {}

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")


async def handle_approve(resource_id: str, user: str, response_url: str) -> None:
    """
    L'utilisateur a cliqué sur ✅ Approuver.
    Récupère l'action en attente et l'exécute.
    """
    pending = PENDING_ACTIONS.pop(resource_id, None)

    if not pending:
        await _update_slack_message(
            response_url,
            text=f"⚠️ Action pour `{resource_id}` introuvable ou déjà traitée.",
            color="#FFA500",
        )
        return

    action_type = pending.get("action_type", "inconnue")
    logger.info("✅ Approuvé par @%s — action '%s' sur '%s'", user, action_type, resource_id)

    # Mise à jour du message Slack immédiatement (UX)
    await _update_slack_message(
        response_url,
        text=f"✅ Action *{action_type}* approuvée par @{user} — exécution en cours...",
        color="#36a64f",
    )

    # Exécution de l'action (import local pour éviter la circularité)
    try:
        from src.executor_client import execute_approved_action
        result = await execute_approved_action(pending)

        await _update_slack_message(
            response_url,
            text=(
                f"✅ Action *{action_type}* sur `{resource_id}` exécutée avec succès par @{user}\n"
                f"```{json.dumps(result, indent=2, default=str)}```"
            ),
            color="#36a64f",
        )
        logger.info("Action '%s' exécutée : %s", action_type, result)

    except Exception as e:
        logger.error("Erreur exécution action '%s': %s", action_type, e, exc_info=True)
        await _update_slack_message(
            response_url,
            text=f"❌ Erreur lors de l'exécution de *{action_type}* sur `{resource_id}` : {e}",
            color="#FF0000",
        )


async def handle_reject(resource_id: str, user: str, response_url: str) -> None:
    """
    L'utilisateur a cliqué sur ❌ Rejeter.
    Annule l'action et met à jour le message Slack.
    """
    pending = PENDING_ACTIONS.pop(resource_id, None)
    action_type = pending.get("action_type", "inconnue") if pending else "inconnue"

    logger.info("❌ Rejeté par @%s — action '%s' sur '%s'", user, action_type, resource_id)

    await _update_slack_message(
        response_url,
        text=f"❌ Action *{action_type}* sur `{resource_id}` rejetée par @{user} — aucune modification effectuée.",
        color="#FF0000",
    )


def register_pending_action(resource_id: str, action_data: dict) -> None:
    """
    Enregistre une action en attente d'approbation.
    Appelé par le Policy Engine avant d'envoyer le message Slack.
    """
    PENDING_ACTIONS[resource_id] = {
        **action_data,
        "registered_at": datetime.utcnow().isoformat(),
    }
    logger.info("⏳ Action '%s' mise en attente pour '%s'", action_data.get("action_type"), resource_id)


async def _update_slack_message(response_url: str, text: str, color: str = "#36a64f") -> None:
    """
    Met à jour le message Slack original via response_url.
    Remplace les boutons par le résultat de l'action.
    """
    payload = {
        "replace_original": True,
        "attachments": [
            {
                "color": color,
                "text": text,
                "footer": f"FinOps Autopilot • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            }
        ],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(response_url, json=payload) as resp:
                if resp.status != 200:
                    logger.error("Erreur mise à jour message Slack : %s", resp.status)
    except Exception as e:
        logger.error("Erreur appel Slack response_url : %s", e)
