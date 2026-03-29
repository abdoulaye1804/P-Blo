# 📁 P-Blo — FinOps Autopilot | Index des fichiers

> Tous les codes du projet classés par ordre de développement.

---

## 01 — Repo Structure
| Fichier | Description |
|---|---|
| `repo-structure.md` | Structure complète du repo GitHub avec conventions |

## 02 — Terraform AWS
| Fichier | Description |
|---|---|
| `backend.tf` | Backend S3 + DynamoDB lock pour le state Terraform |
| `main.tf` | VPC, EKS cluster, IAM IRSA (collector + policy engine) |
| `variables.tf` | Toutes les variables paramétrables |
| `outputs.tf` | Outputs : ARNs, cluster endpoint, commande kubeconfig |
| `terraform.tfvars.example` | Exemple de configuration dev à copier |
| `terraform-plan.yml` | GitHub Actions : plan automatique sur chaque PR |

## 03 — Collector Python
| Fichier | Description |
|---|---|
| `src/main.py` | Entrypoint — boucle de collecte + graceful shutdown |
| `src/providers/aws.py` | AWS Cost Explorer + CloudWatch + EC2 idle + EBS unused |
| `src/kubernetes/metrics.py` | Métriques pods/nodes via Kubernetes Metrics Server |
| `src/kubernetes/exporter.py` | Export des métriques au format Prometheus |
| `src/utils/config.py` | Configuration via variables d'environnement |
| `src/utils/logger.py` | Logger structuré |
| `Dockerfile` | Image Docker Python 3.11 slim, user non-root |
| `requirements.txt` | boto3, kubernetes, prometheus-client |

## 04 — Kubernetes Manifests
| Fichier | Description |
|---|---|
| `namespace.yaml` | Namespace "finops" |
| `rbac.yaml` | ServiceAccounts IRSA + ClusterRoles + Deployment collector |

## 05 — Policy Engine
| Fichier | Description |
|---|---|
| `policies/idle-pods.yaml` | Politique : pods K8s idle (CPU < 5%, RAM < 10%) |
| `policies/oversized-ec2.yaml` | Politique : instances EC2 sous-utilisées (CPU < 10%) |
| `policies/unused-volumes.yaml` | Politique : volumes EBS non attachés depuis 7 jours |
| `src/evaluator.py` | Chargement YAML + évaluation des conditions |
| `src/executor.py` | Exécution des actions (dry-run ou réel) |
| `src/actions/notify.py` | Action : notification Slack avec boutons Approve/Reject |
| `src/actions/resize.py` | Action : scale_down K8s + snapshot_and_stop EC2 |
| `src/actions/snapshot.py` | Action : snapshot + suppression volume EBS |
| `src/main.py` | Entrypoint du Policy Engine |
| `src/utils/config.py` | Configuration via variables d'environnement |

## 06 — Slack Bot
| Fichier | Description |
|---|---|
| `src/main.py` | FastAPI + vérification signature HMAC-SHA256 Slack |
| `src/handlers.py` | Handlers Approve / Reject + mise à jour message |
| `Dockerfile` | Image Docker Python 3.11 slim |
| `requirements.txt` | fastapi, uvicorn, aiohttp, boto3 |

## 07 — Observabilité
| Fichier | Description |
|---|---|
| `grafana/dashboards/costs-overview.json` | Dashboard : coûts AWS, EC2 idle, EBS unused, pods K8s |
| `grafana/dashboards/savings-report.json` | Dashboard : économies réalisées, actions, taux d'approbation |
| `prometheus/prometheus.yaml` | Config Prometheus + autodiscovery K8s |
| `prometheus/alerts.yaml` | Règles d'alerting (coût élevé, instances idle, approbations) |

## 08 — Docs
| Fichier | Description |
|---|---|
| `README.md` | README complet pour GitHub (badges, archi, quickstart, roadmap) |
| `FinOps-Autopilot-Plan-Global.pdf` | Plan global du projet (8 pages) |

---

## 🚀 Ordre de développement recommandé
1. `01` → Créer le repo GitHub avec la structure
2. `02` → Déployer l'infra Terraform (commencer par Minikube en local)
3. `04` → Appliquer les manifests K8s (namespace + RBAC)
4. `03` → Développer et déployer le Collector
5. `05` → Développer le Policy Engine (tout en dry-run)
6. `06` → Développer le Slack Bot
7. `07` → Importer les dashboards Grafana
8. `08` → Finaliser le README et la démo vidéo
