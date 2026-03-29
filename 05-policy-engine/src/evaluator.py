"""
Policy Evaluator — cœur du moteur de politiques.
Charge les fichiers YAML, évalue les conditions contre
les ressources collectées, et déclenche les actions.
"""

import logging
import operator
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Opérateurs supportés dans les conditions YAML
OPERATORS = {
    "lt":  operator.lt,
    "lte": operator.le,
    "gt":  operator.gt,
    "gte": operator.ge,
    "eq":  operator.eq,
    "ne":  operator.ne,
}


class Policy:
    """Représente une politique chargée depuis un fichier YAML."""

    def __init__(self, data: dict) -> None:
        self.name: str = data["name"]
        self.version: str = data.get("version", "1.0")
        self.description: str = data.get("description", "")
        self.enabled: bool = data.get("enabled", True)
        self.scope: dict = data.get("scope", {})
        self.conditions: list[dict] = data.get("conditions", [])
        self.actions: list[dict] = data.get("actions", [])
        self.schedule: dict = data.get("schedule", {})
        self.metadata: dict = data.get("metadata", {})

    def __repr__(self) -> str:
        return f"<Policy name={self.name} enabled={self.enabled}>"


class PolicyEvaluator:
    """
    Charge les politiques YAML et les évalue contre
    les ressources fournies par le Collector.
    """

    def __init__(self, policies_dir: str = "policies") -> None:
        self.policies_dir = Path(policies_dir)
        self.policies: list[Policy] = []

    # ── Chargement ─────────────────────────────────────────────────────────

    def load_policies(self) -> None:
        """Charge tous les fichiers .yaml du dossier policies/."""
        self.policies = []
        for path in sorted(self.policies_dir.glob("*.yaml")):
            try:
                with path.open() as f:
                    data = yaml.safe_load(f)
                policy = Policy(data)
                if policy.enabled:
                    self.policies.append(policy)
                    logger.info("✅ Politique chargée : %s (v%s)", policy.name, policy.version)
                else:
                    logger.info("⏭️  Politique désactivée : %s", policy.name)
            except Exception as e:
                logger.error("❌ Erreur chargement %s : %s", path.name, e)

        logger.info("📋 %d politique(s) active(s)", len(self.policies))

    # ── Évaluation ─────────────────────────────────────────────────────────

    def evaluate(self, resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Évalue toutes les politiques contre la liste de ressources.
        Retourne la liste des violations détectées avec les actions à appliquer.
        """
        violations = []

        for policy in self.policies:
            resource_type = policy.scope.get("resource")
            matching = [r for r in resources if r.get("resource_type") == resource_type]

            logger.debug(
                "Évaluation '%s' — %d ressource(s) de type '%s'",
                policy.name, len(matching), resource_type,
            )

            for resource in matching:
                if self._is_excluded(resource, policy):
                    continue

                if self._evaluate_conditions(resource, policy.conditions):
                    violation = {
                        "policy": policy.name,
                        "severity": policy.metadata.get("severity", "medium"),
                        "resource": resource,
                        "actions": policy.actions,
                        "message": self._build_message(resource, policy),
                    }
                    violations.append(violation)
                    logger.info(
                        "🚨 Violation '%s' sur %s",
                        policy.name,
                        resource.get("id") or resource.get("name"),
                    )

        logger.info(
            "📊 Évaluation terminée — %d violation(s) sur %d ressource(s)",
            len(violations), len(resources),
        )
        return violations

    def _evaluate_conditions(
        self, resource: dict, conditions: list[dict]
    ) -> bool:
        """
        Toutes les conditions doivent être vraies (AND logique).
        Supporte les opérateurs : lt, lte, gt, gte, eq, ne.
        """
        for condition in conditions:
            field = condition["field"]
            op_key = condition["operator"]
            expected = condition["value"]

            actual = resource.get(field)
            if actual is None:
                logger.debug("Champ '%s' absent de la ressource — condition ignorée", field)
                return False

            op_fn = OPERATORS.get(op_key)
            if not op_fn:
                logger.warning("Opérateur inconnu : '%s'", op_key)
                return False

            if not op_fn(actual, expected):
                return False

        return True

    def _is_excluded(self, resource: dict, policy: Policy) -> bool:
        """Vérifie si la ressource doit être exclue selon le scope de la politique."""
        scope = policy.scope

        # Exclusion par namespace (pods K8s)
        if "exclude_namespaces" in scope:
            if resource.get("namespace") in scope["exclude_namespaces"]:
                return True

        # Exclusion par labels
        if "exclude_labels" in scope:
            resource_labels = resource.get("labels", {})
            for key, value in scope["exclude_labels"].items():
                if resource_labels.get(key) == value:
                    return True

        # Exclusion par tags AWS
        if "exclude_tags" in scope:
            resource_tags = resource.get("tags", {})
            for key, value in scope["exclude_tags"].items():
                if resource_tags.get(key) == value:
                    return True

        return False

    @staticmethod
    def _build_message(resource: dict, policy: Policy) -> str:
        """Construit le message de violation en interpolant les champs de la ressource."""
        for action in policy.actions:
            if action["type"] == "notify":
                template = action.get("config", {}).get("message", "")
                try:
                    return template.format(**resource)
                except KeyError:
                    return template
        return f"Violation de la politique '{policy.name}'"
