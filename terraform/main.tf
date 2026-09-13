terraform {
  required_version = ">= 1.14.0"

  # Dynamic S3 backend initialized via GitHub Actions -backend-config
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "CloudNative-AIOps"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

# Data source for Availability Zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Existing VPC Lookup (used if var.vpc_id is provided)
data "aws_vpc" "selected" {
  count = var.vpc_id != "" ? 1 : 0
  id    = var.vpc_id
}

# Managed VPC Module (used if var.vpc_id is NOT provided)
module "vpc" {
  count   = var.vpc_id == "" ? 1 : 0
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = 1
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = 1
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "karpenter.sh/discovery"                    = var.cluster_name
  }
}

# Locals to resolve final VPC & Subnet IDs
locals {
  vpc_id          = var.vpc_id != "" ? var.vpc_id : module.vpc[0].vpc_id
  private_subnets = length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : module.vpc[0].private_subnets
  public_subnets  = length(var.public_subnet_ids) > 0 ? var.public_subnet_ids : module.vpc[0].public_subnets
}

# AWS EKS Cluster Module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.10"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  cluster_endpoint_public_access = true

  vpc_id                   = local.vpc_id
  subnet_ids               = local.private_subnets
  control_plane_subnet_ids = local.private_subnets

  # EKS Managed Bootstrap Node Group
  eks_managed_node_groups = {
    bootstrap_workers = {
      name           = "bootstrap-worker-group"
      instance_types = var.node_instance_types

      min_size     = var.min_node_count
      max_size     = var.max_node_count
      desired_size = var.desired_node_count

      capacity_type = "ON_DEMAND"

      labels = {
        role = "bootstrap-worker"
        env  = var.environment
      }

      tags = {
        "k8s.io/cluster-autoscaler/enabled"             = "true"
        "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
        "karpenter.sh/discovery"                        = var.cluster_name
      }
    }
  }

  enable_cluster_creator_admin_permissions = true

  # Grant Karpenter Node Role permission to join the cluster via Access Entries
  node_security_group_tags = {
    "karpenter.sh/discovery" = var.cluster_name
  }
}

# Provider configurations for Kubernetes & Helm
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

provider "kubectl" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  load_config_file       = false
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}
