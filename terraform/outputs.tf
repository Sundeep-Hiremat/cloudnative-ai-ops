output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS control plane"
  value       = module.eks.cluster_security_group_id
}

output "agent_irsa_role_arn" {
  description = "IAM Role ARN for the KubeOps-Aegis Agent service account"
  value       = module.kubeops_agent_irsa.iam_role_arn
}

output "kubeconfig_command" {
  description = "Command to configure kubectl context for this cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "karpenter_controller_role_arn" {
  description = "IAM Role ARN for Karpenter Controller"
  value       = var.enable_karpenter ? module.karpenter_irsa[0].iam_role_arn : ""
}

output "karpenter_node_role_arn" {
  description = "IAM Role ARN for EC2 nodes launched by Karpenter"
  value       = var.enable_karpenter ? aws_iam_role.karpenter_node[0].arn : ""
}
