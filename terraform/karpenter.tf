# ------------------------------------------------------------------------------
# Karpenter SQS Interruption Queue & EventBridge Rules
# ------------------------------------------------------------------------------
resource "aws_sqs_queue" "karpenter_interruption" {
  count                     = var.enable_karpenter ? 1 : 0
  name                      = "${var.cluster_name}-karpenter-interruption"
  message_retention_seconds = 300
  sqs_managed_sse_enabled   = true
}

# SQS Queue Policy for EventBridge
resource "aws_sqs_queue_policy" "karpenter_interruption" {
  count     = var.enable_karpenter ? 1 : 0
  queue_url = aws_sqs_queue.karpenter_interruption[0].url

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = ["events.amazonaws.com", "sqs.amazonaws.com"] }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.karpenter_interruption[0].arn
      }
    ]
  })
}

# ------------------------------------------------------------------------------
# Karpenter Helm Deployment
# ------------------------------------------------------------------------------
resource "helm_release" "karpenter" {
  count            = var.enable_karpenter ? 1 : 0
  name             = "karpenter"
  namespace        = "karpenter"
  create_namespace = true
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "0.37.0"

  set {
    name  = "settings.clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "settings.interruptionQueue"
    value = aws_sqs_queue.karpenter_interruption[0].name
  }

  set {
    name  = "serviceAccount.annotations.aws-role-arn"
    value = module.karpenter_irsa[0].iam_role_arn
  }

  set {
    name  = "settings.isolatedVPC"
    value = "false"
  }

  depends_on = [module.eks]
}

# ------------------------------------------------------------------------------
# Karpenter Default EC2NodeClass & NodePool CRDs
# ------------------------------------------------------------------------------
resource "kubectl_manifest" "karpenter_node_class" {
  count     = var.enable_karpenter ? 1 : 0
  yaml_body = <<YAML
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2
  role: "${aws_iam_role.karpenter_node[0].name}"
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${module.eks.cluster_name}"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${module.eks.cluster_name}"
  tags:
    karpenter.sh/discovery: "${module.eks.cluster_name}"
YAML

  depends_on = [helm_release.karpenter]
}

resource "kubectl_manifest" "karpenter_node_pool" {
  count     = var.enable_karpenter ? 1 : 0
  yaml_body = <<YAML
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      nodeClassRef:
        name: default
      requirements:
        - key: "karpenter.k8s.aws/instance-category"
          operator: In
          values: ["c", "m", "t"]
        - key: "karpenter.k8s.aws/instance-generation"
          operator: Gt
          values: ["2"]
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["spot", "on-demand"]
        - key: "kubernetes.io/arch"
          operator: In
          values: ["amd64"]
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 720h
  limits:
    cpu: "100"
    memory: 400Gi
YAML

  depends_on = [kubectl_manifest.karpenter_node_class]
}
