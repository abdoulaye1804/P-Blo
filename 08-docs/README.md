# 🚀 FinOps Autopilot

> Plateforme multi-cloud de détection et remédiation automatique des dépenses cloud.

![CI](https://github.com/YOUR_ORG/finops-autopilot/actions/workflows/ci.yml/badge.svg)
![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform)
![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes-326CE5?logo=kubernetes)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)
![AWS](https://img.shields.io/badge/Cloud-AWS-FF9900?logo=amazonaws)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

---

## 🎯 Pourquoi ce projet ?

Les outils de FinOps existants (AWS Cost Explorer, Kubecost) **observent** les coûts.  
FinOps Autopilot va plus loin : il **agit** automatiquement selon des politiques définies en code.

```
Collecter → Analyser → Notifier → Approuver → Remédier
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EKS Cluster                          │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  Collector  │───▶│  Analyzer   │───▶│Policy Engine│ │
│  │  (Python)   │    │  (Python)   │    │  (Python)   │ │
│  └──────┬──────┘    └─────────────┘    └──────┬──────┘ │
│         │                                      │        │
│         │ /metrics                             │ actions│
│         ▼                                      ▼        │
│  ┌─────────────┐                      ┌─────────────┐  │
│  │ Prometheus  │                      │  Slack Bot  │  │
│  │  + Grafana  │                      │  (FastAPI)  │  │
│  └─────────────┘                      └─────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                                      │
         ▼                                      ▼
   AWS Cost Explorer                    Slack (Approve/Reject)
   CloudWatch Metrics                   AWS EC2 / EBS actions
```

---

## ✨ Fonctionnalités

- **Collecte multi-source** — AWS Cost Explorer, CloudWatch, Kubernetes Metrics Server
- **Détection automatique** — instances EC2 idle, volumes EBS non attachés, pods K8s sous-utilisés
- **Policy-as-Code** — règles de remédiation définies en YAML, modifiables sans redéploiement
- **Dry-run par défaut** — aucune action destructive sans validation explicite
- **Approval workflow** — boutons Slack ✅ Approuver / ❌ Rejeter avant toute action
- **Observabilité complète** — métriques Prometheus + dashboards Grafana prêts à l'emploi
- **Sécurité IRSA** — zéro credential AWS stocké dans les pods
- **GitOps** — déploiement continu via ArgoCD

---

## 🚀 Démarrage rapide

### Prérequis

- AWS CLI configuré (`aws configure`)
- Terraform >= 1.6
- kubectl
- Python 3.11+

### 1. Déployer l'infrastructure AWS

```bash
cd infra/terraform/aws

# Bootstrap S3 + DynamoDB
terraform init -backend=false
terraform apply -target=aws_s3_bucket.tfstate -target=aws_dynamodb_table.tflock

# Déploiement complet
terraform init
cp terraform.tfvars.example terraform.tfvars  # Éditer les valeurs
terraform apply
```

### 2. Configurer kubectl

```bash
aws eks update-kubeconfig --name finops-autopilot --region eu-west-1
```

### 3. Déployer les services

```bash
# Namespace + RBAC
kubectl apply -f infra/kubernetes/base/

# Remplacer ACCOUNT_ID dans rbac.yaml
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT/g" infra/kubernetes/base/rbac.yaml
kubectl apply -f infra/kubernetes/base/rbac.yaml
```

### 4. Configurer les variables d'environnement

```bash
# Créer les secrets Kubernetes
kubectl create secret generic finops-secrets \
  --namespace finops \
  --from-literal=SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
  --from-literal=SLACK_BOT_TOKEN=xoxb-... \
  --from-literal=SLACK_SIGNING_SECRET=...
```

---

## 📋 Politiques disponibles

| Politique | Ressource | Condition | Action |
|---|---|---|---|
| `idle-pods` | Pod K8s | CPU < 5% ET RAM < 10% depuis 24h | Notify → Scale to zero |
| `oversized-ec2` | EC2 instance | CPU moy < 10% sur 24h | Notify → Snapshot + Stop |
| `unused-volumes` | EBS Volume | Non attaché depuis 7 jours | Notify → Snapshot + Delete |

### Ajouter une politique

Créer un fichier YAML dans `policy-engine/policies/` :

```yaml
name: my-custom-policy
enabled: true
scope:
  resource: ec2_instance
  exclude_tags:
    Environment: prod
conditions:
  - field: avg_cpu_percent
    operator: lt
    value: 5.0
actions:
  - type: notify
    dry_run: false
    config:
      channel: slack
      message: "Instance trop petite : {instance_id}"
      require_approval: true
  - type: snapshot_and_stop
    dry_run: true   # Passer à false quand tu es prêt
    config:
      require_approval: true
schedule:
  interval_minutes: 120
```

Le Policy Engine rechargera automatiquement la politique au prochain cycle. ✨

---

## 📊 Dashboards Grafana

| Dashboard | Description |
|---|---|
| **Costs Overview** | Coût mensuel, top services, EC2 idle, volumes EBS |
| **Savings Report** | Économies réalisées, actions par type, taux d'approbation |

Importer les fichiers JSON depuis `observability/grafana/dashboards/`.

---

## 🔐 Sécurité

- **IRSA** — chaque pod a son propre rôle IAM minimal (principe de moindre privilège)
- **Dry-run par défaut** — `dry_run: true` dans toutes les nouvelles politiques
- **Approval workflow** — actions destructives soumises à validation humaine via Slack
- **Scope tags** — le Policy Engine n'agit que sur les ressources taguées `ManagedBy: finops-autopilot`
- **Signature Slack** — vérification HMAC-SHA256 sur chaque webhook entrant

---

## 🗺️ Roadmap

- [x] Collector AWS (Cost Explorer + EC2 + EBS)
- [x] Collector Kubernetes (pods + nodes)
- [x] Policy Engine (évaluateur + exécuteur)
- [x] Slack Bot (approval workflow)
- [x] Dashboards Grafana
- [ ] Support Azure Cost Management
- [ ] Support GCP Billing API
- [ ] Interface web de gestion des politiques
- [ ] Rapport PDF mensuel automatique

---

## 🤝 Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📄 Licence

Apache 2.0 — voir [LICENSE](LICENSE).
