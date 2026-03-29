# ─────────────────────────────────────────────
# OUTPUTS CLUSTER EKS
# ─────────────────────────────────────────────

output "cluster_name" {
  description = "Nom du cluster EKS"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint de l'API server EKS"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "cluster_certificate_authority_data" {
  description = "Certificate Authority du cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "URL OIDC du cluster (pour IRSA)"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_provider_arn" {
  description = "ARN du provider OIDC (pour IRSA)"
  value       = module.eks.oidc_provider_arn
}

# ─────────────────────────────────────────────
# OUTPUTS VPC
# ─────────────────────────────────────────────

output "vpc_id" {
  description = "ID du VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "IDs des subnets privés"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "IDs des subnets publics"
  value       = module.vpc.public_subnets
}

# ─────────────────────────────────────────────
# OUTPUTS IAM ROLES (IRSA)
# ─────────────────────────────────────────────

output "finops_collector_role_arn" {
  description = "ARN du rôle IAM pour le Collector (à annoter sur le ServiceAccount K8s)"
  value       = module.finops_collector_irsa.iam_role_arn
}

output "finops_policy_engine_role_arn" {
  description = "ARN du rôle IAM pour le Policy Engine"
  value       = module.finops_policy_engine_irsa.iam_role_arn
}

output "cluster_autoscaler_role_arn" {
  description = "ARN du rôle IAM pour le Cluster Autoscaler"
  value       = module.cluster_autoscaler_irsa.iam_role_arn
}

# ─────────────────────────────────────────────
# COMMANDE KUBECONFIG (pratique)
# ─────────────────────────────────────────────

output "kubeconfig_command" {
  description = "Commande pour configurer kubectl"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}
