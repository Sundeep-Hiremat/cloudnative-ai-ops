# IAM Role for Service Accounts (IRSA) for KubeOps-Aegis Agent
module "kubeops_agent_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name = "${var.cluster_name}-agent-irsa"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["default:kubeops-agent-sa"]
    }
  }

  role_policy_arns = {
    cloudwatch_readonly = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
  }
}

# Custom Policy for Agent to inspect EKS cluster and nodes
resource "aws_iam_policy" "kubeops_eks_read" {
  name        = "${var.cluster_name}-eks-read-policy"
  description = "Allows KubeOps-Aegis agent to describe cluster nodes and metrics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters",
          "eks:DescribeNodegroup",
          "eks:ListNodegroups"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kubeops_eks_read_attach" {
  role       = module.kubeops_agent_irsa.iam_role_name
  policy_arn = aws_iam_policy.kubeops_eks_read.arn
}

# ------------------------------------------------------------------------------
# Karpenter IAM Configuration
# ------------------------------------------------------------------------------

# Karpenter Controller IRSA Module
module "karpenter_irsa" {
  count   = var.enable_karpenter ? 1 : 0
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name                          = "${var.cluster_name}-karpenter-controller"
  attach_karpenter_controller_policy = true

  karpenter_controller_node_iam_role_arns = [
    aws_iam_role.karpenter_node[0].arn
  ]

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["karpenter:karpenter"]
    }
  }
}

# Karpenter Node IAM Role (Assumed by EC2 instances launched by Karpenter)
resource "aws_iam_role" "karpenter_node" {
  count = var.enable_karpenter ? 1 : 0
  name  = "${var.cluster_name}-karpenter-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach Standard Policies to Karpenter Node Role
resource "aws_iam_role_policy_attachment" "karpenter_worker_node" {
  count      = var.enable_karpenter ? 1 : 0
  role       = aws_iam_role.karpenter_node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "karpenter_cni_policy" {
  count      = var.enable_karpenter ? 1 : 0
  role       = aws_iam_role.karpenter_node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "karpenter_registry_policy" {
  count      = var.enable_karpenter ? 1 : 0
  role       = aws_iam_role.karpenter_node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "karpenter_ssm_policy" {
  count      = var.enable_karpenter ? 1 : 0
  role       = aws_iam_role.karpenter_node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Access Entry giving Karpenter Node Role rights to join the EKS cluster
resource "aws_eks_access_entry" "karpenter_node" {
  count         = var.enable_karpenter ? 1 : 0
  cluster_name  = module.eks.cluster_name
  principal_arn = aws_iam_role.karpenter_node[0].arn
  type          = "EC2_LINUX"
}
