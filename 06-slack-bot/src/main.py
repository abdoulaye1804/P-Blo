#!/usr/bin/env python3
"""
FinOps Autopilot — Slack Bot
Reçoit les interactions Slack (boutons Approve / Reject)
et déclenche ou annule les actions du Policy Engine.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.handlers import handle_approve, handle_reject
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="FinOps Autopilot — Slack Bot", version="1.0.0")

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")


# ── Vérification signature Slack ───────────────────────────────────────────

def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """
    Vérifie que la requête vient bien de Slack (HMAC-SHA256).
    Protège contre les requêtes forgées.
    """
    # Rejeter les requêtes trop vieilles (replay attack)
    if abs(time.time() - int(timestamp)) > 300:
        logger.warning("⚠️  Requête Slack trop ancienne — possible replay attack")
        return False

    base = f"v0:{timestamp}:{request_body.decode()}"
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/slack/interactions")
async def slack_interactions(request: Request) -> JSONResponse:
    """
    Endpoint appelé par Slack quand l'utilisateur clique
    sur un bouton Approve ou Reject dans un message.
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Vérification de la signature
    if SLACK_SIGNING_SECRET and not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Signature Slack invalide")

    # Décodage du payload Slack (application/x-www-form-urlencoded)
    from urllib.parse import parse_qs, unquote_plus
    import json

    parsed = parse_qs(body.decode())
    payload = json.loads(unquote_plus(parsed.get("payload", ["{}"])[0]))

    action_id = payload.get("actions", [{}])[0].get("action_id", "")
    action_value = payload.get("actions", [{}])[0].get("value", "")
    user = payload.get("user", {}).get("name", "unknown")
    response_url = payload.get("response_url", "")

    logger.info("📩 Interaction Slack — action: %s | user: %s", action_id, user)

    if action_id == "finops_approve":
        _, resource_id = action_value.split(":", 1)
        await handle_approve(resource_id=resource_id, user=user, response_url=response_url)

    elif action_id == "finops_reject":
        _, resource_id = action_value.split(":", 1)
        await handle_reject(resource_id=resource_id, user=user, response_url=response_url)

    else:
        logger.warning("Action inconnue reçue : %s", action_id)

    # Slack attend une réponse 200 rapide
    return JSONResponse(content={"ok": True})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
