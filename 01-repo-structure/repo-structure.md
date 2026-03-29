# 📁 FinOps Autopilot — Structure du repo GitHub

```
finops-autopilot/
│
├── 📄 README.md                          # Présentation du projet, badges, architecture diagram
├── 📄 LICENSE                            # MIT ou Apache 2.0
├── 📄 CONTRIBUTING.md                    # Guide de contribution
├── 📄 CHANGELOG.md                       # Historique des versions
├── 📄 .gitignore
├── 📄 .env.example                       # Variables d'env (jamais le .env réel !)
│
├── 📁 .github/
│   ├── 📁 workflows/
│   │   ├── ci.yml                        # Lint + tests à chaque PR
│   │   ├── terraform-plan.yml            # Terraform plan automatique sur PR
│   │   └── release.yml                   # Build & push Docker image sur tag
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── 📁 infra/                             # Tout ce qui est IaC
│   ├── 📁 terraform/
│   │   ├── 📁 aws/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── backend.tf                # State S3 + DynamoDB lock
│   │   ├── 📁 azure/
│   │   │   ├── main.tf
│   │   │   └── variables.tf
│   │   ├── 📁 gcp/
│   │   │   ├── main.tf
│   │   │   └── variables.tf
│   │   └── 📁 modules/
│   │       ├── 📁 eks/                   # Module Kubernetes cluster AWS
│   │       ├── 📁 iam/                   # Roles & policies
│   │       └── 📁 monitoring/            # Prometheus + Grafana stack
│   │
│   └── 📁 kubernetes/
│       ├── 📁 base/                      # Manifests de base (Kustomize)
│       │   ├── namespace.yaml
│       │   ├── rbac.yaml
│       │   └── kustomization.yaml
│       ├── 📁 overlays/
│       │   ├── 📁 dev/
│       │   └── 📁 prod/
│       └── 📁 argocd/
│           ├── application.yaml
│           └── project.yaml
│
├── 📁 collector/                         # Agent de collecte de métriques
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📁 src/
│   │   ├── __init__.py
│   │   ├── main.py                       # Entrypoint
│   │   ├── 📁 providers/
│   │   │   ├── aws.py                    # AWS Cost Explorer API
│   │   │   ├── azure.py                  # Azure Cost Management API
│   │   │   └── gcp.py                    # GCP Billing API
│   │   ├── 📁 kubernetes/
│   │   │   ├── metrics.py                # Collecte métriques pods/nodes
│   │   │   └── exporter.py               # Export vers Prometheus
│   │   └── 📁 utils/
│   │       ├── logger.py
│   │       └── config.py
│   └── 📁 tests/
│       ├── test_aws.py
│       ├── test_azure.py
│       └── test_kubernetes.py
│
├── 📁 analyzer/                          # Moteur d'analyse & détection
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📁 src/
│   │   ├── main.py
│   │   ├── detector.py                   # Détection ressources sous-utilisées
│   │   ├── scorer.py                     # Scoring & priorisation
│   │   └── recommender.py                # Génération de recommandations
│   └── 📁 tests/
│
├── 📁 policy-engine/                     # Moteur de politiques (cœur du projet)
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📁 src/
│   │   ├── main.py
│   │   ├── evaluator.py                  # Évaluation des politiques YAML
│   │   ├── executor.py                   # Exécution des actions
│   │   └── 📁 actions/
│   │       ├── resize.py                 # Rightsizing EC2 / pods
│   │       ├── snapshot.py               # Snapshot + destroy
│   │       └── notify.py                 # Slack / PagerDuty
│   ├── 📁 policies/                      # Politiques définies en YAML
│   │   ├── idle-pods.yaml
│   │   ├── oversized-ec2.yaml
│   │   └── unused-volumes.yaml
│   └── 📁 tests/
│
├── 📁 slack-bot/                         # Bot d'approbation des actions
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   └── 📁 src/
│       ├── main.py
│       ├── handlers.py                   # Gestion des boutons Approve / Reject
│       └── formatter.py                  # Formatage des messages Slack
│
├── 📁 observability/                     # Stack monitoring
│   ├── 📁 grafana/
│   │   ├── 📁 dashboards/
│   │   │   ├── costs-overview.json
│   │   │   ├── actions-history.json
│   │   │   └── savings-report.json
│   │   └── datasources.yaml
│   └── 📁 prometheus/
│       ├── prometheus.yaml
│       └── alerts.yaml
│
├── 📁 docs/                              # Documentation
│   ├── architecture.md                   # Diagram + explications
│   ├── getting-started.md                # Guide d'installation
│   ├── policies-reference.md             # Référence des politiques YAML
│   └── 📁 diagrams/
│       └── architecture.drawio           # Fichier source du schéma
│
└── 📁 scripts/                           # Scripts utilitaires
    ├── setup.sh                          # Bootstrap de l'environnement local
    ├── deploy.sh                         # Déploiement complet
    └── generate-report.py                # Rapport de savings en PDF
```

---

## 🏷️ Badges recommandés pour le README

```markdown
![CI](https://github.com/ton-user/finops-autopilot/actions/workflows/ci.yml/badge.svg)
![Terraform](https://img.shields.io/badge/IaC-Terraform-purple)
![Kubernetes](https://img.shields.io/badge/orchestration-Kubernetes-blue)
![Python](https://img.shields.io/badge/python-3.11+-yellow)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
```

---

## 🚀 Commandes pour initialiser le repo

```bash
# Créer la structure d'un coup
mkdir -p finops-autopilot/{.github/{workflows,ISSUE_TEMPLATE},infra/{terraform/{aws,azure,gcp,modules/{eks,iam,monitoring}},kubernetes/{base,overlays/{dev,prod},argocd}},collector/{src/{providers,kubernetes,utils},tests},analyzer/{src,tests},policy-engine/{src/actions,policies,tests},slack-bot/src,observability/{grafana/dashboards,prometheus},docs/diagrams,scripts}

cd finops-autopilot
git init
git checkout -b main
```

---

## 📌 Conventions à respecter

| Élément | Convention |
|---|---|
| Branches | `main`, `develop`, `feat/xxx`, `fix/xxx` |
| Commits | Conventional Commits (`feat:`, `fix:`, `chore:`) |
| Versioning | Semantic Versioning (v1.0.0) |
| Images Docker | Tag = version git (`ghcr.io/user/finops-autopilot:v1.0.0`) |
| Secrets | Jamais dans le repo — Vault ou AWS Secrets Manager |
