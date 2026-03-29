"""
Action Notify — envoie un message Slack avec boutons Approve / Reject.
Si require_approval=True, l'action suivante attend la réponse de l'utilisateur.
"""

import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class NotifyAction:
    """Envoie une notification Slack et gère optionnellement l'approbation."""

    def __init__(
        self,
        resource: dict,
        config: dict,
        dry_run: bool = True,
        aws_region: str = "eu-west-1",
    ) -> None:
        self.resource = resource
        self.config = config
        self.dry_run = dry_run
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")

    async def execute(self) -> dict[str, Any]:
        """Envoie le message Slack avec ou sans boutons d'approbation."""
        import aiohttp

        message = self.config.get("message", "Violation FinOps détectée")
        require_approval = self.config.get("require_approval", False)

        payload = self._build_payload(message, require_approval)

        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Slack API error: {resp.status}")

        logger.info("📢 Notification Slack envoyée — approval requis: %s", require_approval)
        return {"notified": True, "require_approval": require_approval}

    async def dry_run(self) -> dict[str, Any]:
        message = self.config.get("message", "Violation FinOps détectée")
        logger.info("[DRY-RUN] Notification Slack : %s", message)
        return {"notified": False, "dry_run": True, "message": message}

    def _build_payload(self, message: str, require_approval: bool) -> dict:
        """Construit le bloc Slack avec ou sans boutons d'approbation."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ FinOps Autopilot — Action requise"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ressource :*\n`{self.resource.get('id', 'N/A')}`"},
                    {"type": "mrkdwn", "text": f"*Type :*\n{self.resource.get('resource_type', 'N/A')}"},
                ],
            },
        ]

        if require_approval:
            resource_id = self.resource.get("id") or self.resource.get("name", "unknown")
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approuver"},
                        "style": "primary",
                        "value": f"approve:{resource_id}",
                        "action_id": "finops_approve",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Rejeter"},
                        "style": "danger",
                        "value": f"reject:{resource_id}",
                        "action_id": "finops_reject",
                    },
                ],
            })

        return {"blocks": blocks}
