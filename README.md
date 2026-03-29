<div align="center">

<br/>

```
███████╗██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
█████╗  ██║██╔██╗ ██║██║   ██║██████╔╝███████╗
██╔══╝  ██║██║╚██╗██║██║   ██║██╔═══╝ ╚════██║
██║     ██║██║ ╚████║╚██████╔╝██║     ███████║
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚══════╝
         AUTOPILOT — Cloud Cost Remediation
```

**Stop observing. Start remediating.**

Détection automatique + remédiation active des dépenses cloud inutiles,
pilotée par des politiques définies en code YAML.

<br/>

[![CI](https://img.shields.io/github/actions/workflow/status/
abdoulaye1804/P-Blo/ci.yml?branch=main&label=CI&logo=github&style=flat-square)](https://github.com/YOUR_ORG/finops-autopilot/actions)
[![Terraform](https://img.shields.io/badge/IaC-Terraform_1.6+-7B42BC?style=flat-square&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/K8s-EKS_1.29-326CE5?style=flat-square&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![AWS](https://img.shields.io/badge/Cloud-AWS-FF9900?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![Prometheus](https://img.shields.io/badge/Metrics-Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Dashboards-Grafana-F46800?style=flat-square&logo=grafana&logoColor=white)](https://grafana.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-22C55E?style=flat-square)](./LICENSE)

<br/>

>  **Résultat :** -30% de dépenses cloud sur l'environnement de test en 3 semaines
> grâce à la détection de 12 instances EC2 idle et 8 volumes EBS orphelins.

<br/>

</div>

---

##  Le problème que ce projet résout

| Outil existant | Observe les coûts | Agit automatiquement | Policy-as-Code | K8s natif |
|---|:---:|:---:|:---:|:---:|
| AWS Cost Explorer | ✅ | ❌ | ❌ | ❌ |
| Kubecost / OpenCost | ✅ | ❌ | ❌ | ✅ |
| Cloud Custodian | ✅ | ✅ | ✅ | ⚠️ |
| **FinOps Autopilot** | ✅ | ✅ | ✅ | ✅ |

**FinOps Autopilot** est la seule solution qui combine les 4 — et c'est toi qui l'as construite.

---

##  Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         EKS Cluster  (eu-west-1)                     │
│                                                                       │
│   ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│   │  Collector   │───▶│   Analyzer   │───▶│    Policy Engine      │  │
│   │              │    │              │    │                       │  │
│   │ • Cost Expl. │    │ • Scoring    │    │ • YAML loader         │  │
│   │ • CloudWatch │    │ • Anomaly    │    │ • Condition eval      │  │
│   │ • K8s Metrics│    │   detection  │    │ • Action executor     │  │
│   └──────┬───────┘    └──────────────┘    └──────────┬────────────┘  │
│          │ /metrics                                   │               │
│          ▼                                            ▼               │
│   ┌──────────────┐                         ┌──────────────────────┐  │
│   │  Prometheus  │◀────── scrape ──────────│    Slack Bot         │  │
│   │  + Grafana   │                         │    (FastAPI)         │  │
│   └──────────────┘                         └──────────┬───────────┘  │
│                                                        │              │
└────────────────────────────────────────────────────────┼─────────────┘
                                                         │
                    ┌────────────────────────────────────▼──────────┐
                    │                  Slack                         │
                    │   ┌──────────────────────────────────────┐    │
                    │   │  ⚠️ EC2 i-0a1b2c3d idle (CPU: 3.2%)  │    │
                    │   │  Coût estimé : $47/mois               │    │
                    │   │  [✅ Approuver]  [❌ Rejeter]         │    │
                    │   └──────────────────────────────────────┘    │
                    └───────────────────────────────────────────────┘
```

### Flux de données

```
AWS Cost Explorer ──┐
CloudWatch Metrics ─┼──▶ Collector ──▶ Prometheus ──▶ Grafana
K8s Metrics Server ─┘         │
                               │
                               ▼
                         Policy Engine ──▶ Évalue les politiques YAML
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             [dry_run: true]      [require_approval: true]
             Log uniquement       Slack Bot ──▶ Action AWS/K8s
```

---

##  Fonctionnalités clés

###  Détection multi-source

```python
# Exemple de détection — instances EC2 idle (CPU < 10% sur 24h)
idle = await aws.get_idle_ec2_instances(cpu_threshold=10.0, lookback_hours=24)
# → [{'id': 'i-0a1b2c3d', 'type': 't3.medium', 'avg_cpu_percent': 3.2, ...}]
```

| Source | Ce qui est détecté |
|---|---|
| AWS Cost Explorer | Coût mensuel par service, anomalies de facturation |
| CloudWatch | Instances EC2 avec CPU chroniquement bas |
| EC2 API | Volumes EBS non attachés depuis +7 jours |
| K8s Metrics Server | Pods avec CPU < 5% et RAM < 10% |

###  Policy-as-Code — règles en YAML

```yaml
# policy-engine/policies/idle-pods.yaml
name: idle-pods
enabled: true

conditions:
  - field: cpu_usage_percent
    operator: lt
    value: 5.0
  - field: age_hours
    operator: gte
    value: 24

actions:
  - type: notify
    config:
      message: "Pod idle : {namespace}/{name} — CPU: {cpu_usage_percent}%"
      require_approval: false

  - type: scale_down
    dry_run: false           # ← passer à true pour désactiver
    config:
      replicas: 0
      require_approval: true # ← validation Slack obligatoire
```

> **Le moteur recharge les politiques à chaque cycle** — modifie un YAML, l'effet est immédiat sans redéploiement.

###  Sécurité IRSA — zéro credential dans les pods

```hcl
# Terraform — chaque service a son propre rôle IAM minimal
module "finops_collector_irsa" {
  source = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

  oidc_providers = {
    main = {
      namespace_service_accounts = ["finops:collector-sa"]
    }
  }
}

# IAM policy : lecture seule Cost Explorer + CloudWatch
# Aucun credential stocké dans le pod — EKS gère l'injection automatiquement
```

```yaml
# Kubernetes — annotation suffisante pour l'auth AWS complète
apiVersion: v1
kind: ServiceAccount
metadata:
  name: collector-sa
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789:role/finops-collector"
```

###  Workflow d'approbation Slack

```
Policy Engine détecte une violation
         │
         ▼
Notification Slack avec contexte (ressource, coût, recommandation)
         │
    ┌────┴─────┐
    ▼          ▼
[Approuver]  [Rejeter]
    │              │
    ▼              ▼
Action exécutée   Annulé — aucune modification
(snapshot + stop) Log de la décision conservé
```

---

##  Démarrage rapide

### Prérequis

```bash
# Vérifier les outils
terraform --version   # >= 1.6.0
kubectl version       # >= 1.29
aws --version         # >= 2.0
python --version      # >= 3.11
```

### 1. Déployer l'infrastructure

```bash
cd 02-terraform-aws

# Bootstrap du backend S3 + DynamoDB (une seule fois)
terraform init -backend=false
terraform apply \
  -target=aws_s3_bucket.tfstate \
  -target=aws_dynamodb_table.tflock

# Déploiement complet
cp terraform.tfvars.example terraform.tfvars
# Éditer terraform.tfvars avec tes valeurs
terraform init && terraform apply
```

### 2. Configurer kubectl

```bash
aws eks update-kubeconfig \
  --name finops-autopilot \
  --region eu-west-1
```

### 3. Déployer les services

```bash
# Namespace + RBAC
kubectl apply -f 04-k8s-manifests/namespace.yaml

# Injecter ton AWS Account ID
export AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT/g" 04-k8s-manifests/rbac.yaml
kubectl apply -f infra/kubernetes/base/rbac.yaml

# Secrets Slack
kubectl create secret generic finops-secrets \
  --namespace finops \
  --from-literal=SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
  --from-literal=SLACK_BOT_TOKEN=xoxb-... \
  --from-literal=SLACK_SIGNING_SECRET=...
```

### 4. Vérifier que tout tourne

```bash
kubectl get pods -n finops
# NAME                           READY   STATUS    RESTARTS
# collector-6d9f8b7c4-xk9p2      1/1     Running   0
# policy-engine-7c8d9f4b5-mn3q1  1/1     Running   0
# slack-bot-5f6g7h8i9-op4r5      1/1     Running   0

# Vérifier les métriques
kubectl port-forward svc/collector 8000:8000 -n finops
curl localhost:8000/metrics | grep finops_aws_monthly_cost
# finops_aws_monthly_cost_usd 847.23
```

---

##  Politiques disponibles

| Politique | Ressource | Condition | Action | Dry-run |
|---|---|---|---|:---:|
| `idle-pods` | Pod K8s | CPU < 5% ET RAM < 10% depuis 24h | Notify → Scale to zero | ✅ |
| `oversized-ec2` | EC2 instance | CPU moy. < 10% sur 24h | Notify → Snapshot + Stop | ✅ |
| `unused-volumes` | EBS Volume | Non attaché depuis 7 jours | Notify → Snapshot + Delete | ❌ |

### Ajouter ta propre politique en 5 minutes

```yaml
# policy-engine/policies/ma-politique.yaml
name: my-policy
version: "1.0"
enabled: true

scope:
  resource: ec2_instance
  exclude_tags:
    Environment: prod       # ← jamais d'action en prod

conditions:
  - field: avg_cpu_percent
    operator: lt
    value: 5.0

actions:
  - type: notify
    dry_run: false
    config:
      channel: slack
      message: "Instance très idle : {instance_id} — CPU: {avg_cpu_percent}%"
      require_approval: true

schedule:
  interval_minutes: 120
```

> Le Policy Engine détecte le nouveau fichier au prochain cycle — **aucun redéploiement nécessaire**.

---

##  Dashboards Grafana

Deux dashboards prêts à l'emploi dans `07-observability/grafana/dashboards/` :

| Dashboard | Métriques clés |
|---|---|
| **Costs Overview** | Coût mensuel AWS, top 10 services, EC2 idle, volumes EBS, pods K8s |
| **Savings Report** | Économies réalisées, actions exécutées, taux d'approbation |

**Import rapide :**

```bash
# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Puis : Grafana UI → Dashboards → Import → Upload JSON
# Fichiers : observability/grafana/dashboards/*.json
```

---

##  Sécurité

### 3 niveaux de protection contre les actions accidentelles

```
Niveau 1 : dry_run: true dans le YAML
           └─▶ Log uniquement, aucune modification réelle

Niveau 2 : require_approval: true
           └─▶ Bouton Slack obligatoire avant exécution

Niveau 3 : exclude_tags: Environment: prod
           └─▶ Politique ne s'applique jamais aux ressources de prod
```

### Principe de moindre privilège (IRSA)

| Service Account | Permissions AWS |
|---|---|
| `collector-sa` | Lecture seule : Cost Explorer, CloudWatch, EC2 describe |
| `policy-engine-sa` | Actions EC2/EBS **uniquement** sur ressources taguées `ManagedBy: finops-autopilot` |
| `cluster-autoscaler-sa` | Gestion Auto Scaling Groups uniquement |

---

##  Structure du projet

```
finops-autopilot/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint + tests Python
│       └── terraform-plan.yml        # Plan auto sur chaque PR
│
├── infra/
│   ├── terraform/aws/
│   │   ├── main.tf                   # EKS + VPC + IRSA
│   │   ├── backend.tf                # State S3 + DynamoDB lock
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── kubernetes/base/
│       ├── namespace.yaml
│       └── rbac.yaml                 # ServiceAccounts + ClusterRoles
│
├── collector/                        # Microservice Python — collecte
│   ├── src/
│   │   ├── providers/aws.py          # Cost Explorer + CloudWatch + EC2
│   │   ├── kubernetes/metrics.py     # Pods + nodes via Metrics Server
│   │   └── kubernetes/exporter.py   # Export Prometheus
│   └── Dockerfile
│
├── policy-engine/                    # Microservice Python — remédiation
│   ├── policies/
│   │   ├── idle-pods.yaml
│   │   ├── oversized-ec2.yaml
│   │   └── unused-volumes.yaml
│   ├── src/
│   │   ├── evaluator.py              # Chargement YAML + conditions
│   │   ├── executor.py               # Chaîne d'actions
│   │   └── actions/                 # notify, scale_down, snapshot
│   └── Dockerfile
│
├── slack-bot/                        # Microservice Python — approbation
│   ├── src/
│   │   ├── main.py                   # FastAPI + HMAC-SHA256
│   │   └── handlers.py              # Approve / Reject
│   └── Dockerfile
│
└── observability/
    ├── grafana/dashboards/           # costs-overview.json, savings-report.json
    └── prometheus/                   # prometheus.yaml, alerts.yaml
```

---

##  Roadmap

- [x] Collector AWS (Cost Explorer + EC2 + EBS)
- [x] Collector Kubernetes (pods + nodes)
- [x] Policy Engine — évaluateur YAML + exécuteur d'actions
- [x] Actions : `scale_down`, `snapshot_and_stop`, `snapshot_and_delete`
- [x] Slack Bot — workflow d'approbation avec HMAC-SHA256
- [x] Dashboards Grafana + alertes Prometheus
- [x] IRSA — zéro credential dans les pods
- [x] CI/CD — Terraform plan sur PR, build Docker
- [ ] Support Azure Cost Management API
- [ ] Support GCP Billing API
- [ ] Interface web de gestion des politiques
- [ ] Rapport PDF mensuel automatique (`scripts/generate-report.py`)
- [ ] Intégration OPA / Rego pour les politiques avancées

---

##  Contribuer

Les contributions sont les bienvenues ! Consulter [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

```bash
# Setup de l'environnement de dev
git clone https://github.com/abdoulaye1804/P-Blot
cd finops-autopilot
python -m venv .venv && source .venv/bin/activate
pip install -r 03-collector/requirements.txt
pip install -r 05-policy-engine/requirements.txt

# Lancer les tests
pytest collector/tests/ policy-engine/tests/ -v

# Tester en local avec Minikube
minikube start --cpus=4 --memory=8192
kubectl apply -f infra/kubernetes/base/
```

---

##  Licence

Apache 2.0 — voir [LICENSE](LICENSE).

---

<div align="center">

**Construit avec 🚀 par un ingénieur systèmes, réseaux & cloud**

*Architecture microservices · Kubernetes EKS · Terraform · Python · FinOps*

</div>
