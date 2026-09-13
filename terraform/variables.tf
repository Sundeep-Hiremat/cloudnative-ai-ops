variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment (e.g. prd, dev, stg)"
  type        = string
  default     = "prd"
}

variable "cluster_name" {
  description = "Name of the AWS EKS Cluster"
  type        = string
  default     = "kubeops-ai-prd-cluster"
}

variable "cluster_version" {
  description = "Kubernetes version for AWS EKS control plane (e.g., 1.30, 1.31)"
  type        = string
  default     = "1.30"
}

# Optional Existing VPC Integration
variable "vpc_id" {
  description = "Optional existing VPC ID. If left empty, Terraform will provision a new VPC module."
  type        = string
  default     = ""
}

variable "private_subnet_ids" {
  description = "Optional existing private subnet IDs for EKS worker nodes and control plane ENIs."
  type        = list(string)
  default     = []
}

variable "public_subnet_ids" {
  description = "Optional existing public subnet IDs for internet-facing LoadBalancers and IGW."
  type        = list(string)
  default     = []
}

variable "vpc_cidr" {
  description = "CIDR block for VPC creation (used when vpc_id is empty)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS bootstrap managed node group"
  type        = list(string)
  default     = ["t3.medium", "t3a.medium"]
}

variable "desired_node_count" {
  description = "Desired number of bootstrap worker nodes"
  type        = number
  default     = 3
}

variable "min_node_count" {
  description = "Minimum number of bootstrap worker nodes"
  type        = number
  default     = 2
}

variable "max_node_count" {
  description = "Maximum number of bootstrap worker nodes"
  type        = number
  default     = 6
}

variable "enable_karpenter" {
  description = "Whether to enable Karpenter Just-In-Time node autoscaling"
  type        = bool
  default     = true
}
