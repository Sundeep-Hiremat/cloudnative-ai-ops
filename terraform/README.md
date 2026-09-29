# ⚡ KubeOps-Aegis AWS EKS Infrastructure & Architecture Knowledge Guide

This directory contains the production Infrastructure-as-Code (IaC) for **KubeOps-Aegis**, built using **Terraform**, **AWS EKS 1.30/1.31**, **Karpenter Just-In-Time Autoscaling**, **ArgoCD**, and **Prometheus Stack**.

---

## 📚 Table of Contents
1. [Architectural Knowledge & Core Concepts](#-1-architectural-knowledge--core-concepts)
   - [Why Use Terraform Modules?](#-why-use-terraform-modules)
   - [Why Provider Configurations for Kubernetes, Helm, & Kubectl Are Required](#-why-provider-configurations-for-kubernetes-helm--kubectl-are-required)
   - [Why `gavinbunney/kubectl` Provider Is Used](#-why-gavinbunneykubectl-provider-is-used)
2. [Compute Management & Karpenter Deep-Dive](#-2-compute-management--karpenter-deep-dive)
   - [Why Karpenter Is Required](#-why-karpenter-is-required)
   - [Why the SQS Interruption Queue Exists](#-why-the-sqs-interruption-queue-exists)
3. [Pods & Addon Infrastructure](#-3-pods--addon-infrastructure)
   - [How Prometheus Stack Operates](#-how-prometheus-stack-operates)
   - [How ArgoCD Operates](#-how-argocd-operates)
4. [Deployment Instructions](#-4-deployment-instructions)
   - [Ultra-Low Cost Configuration (`env/prd.tfvars`)](#-ultra-low-cost-configuration-envprdtfvars)
   - [GitHub Actions CI/CD Triggering](#-github-actions-cicd-triggering)
   - [Local Terraform Commands](#-local-terraform-commands)

---

## 🏛️ 1. Architectural Knowledge & Core Concepts

### 📦 Why Use Terraform Modules?
In production infrastructure, creating AWS VPCs and EKS clusters from scratch without modules requires writing over **600+ lines of repetitive HCL boilerplate** for IAM role trust policies, security group rules, subnets, launch templates, and KMS encryption keys.

- **Community Modules (`terraform-aws-modules/eks/aws`, `terraform-aws-modules/vpc/aws`)**: Official modules actively maintained by AWS and HashiCorp. They incorporate security best practices, handle edge cases across AWS API updates, and ensure clean maintainability.
- **Enterprise Corporate Use**: Startups and mid-sized enterprises use community modules directly. Large enterprises create **Internal Wrapper Modules** (published to private registries like Terraform Cloud or Artifactory) that wrap community modules while enforcing mandatory corporate guardrails (e.g., compulsory tags, strict CIDR rules, and mandatory KMS encryption).

---

### 🔑 Why Provider Configurations for Kubernetes, Helm, & Kubectl Are Required

In `main.tf`, you notice three non-AWS provider blocks:

```hcl
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" { ... }
provider "kubectl" { ... }
```

#### Why are these needed?
1. **The `aws` Provider**: Communicates with AWS APIs to create the physical infrastructure (VPC, EKS cluster control plane, EC2 node groups, IAM roles).
2. **The `kubernetes`, `helm`, and `kubectl` Providers**: Communicate directly with the **Kubernetes API Server Endpoint** (`module.eks.cluster_endpoint`) to deploy workloads (ArgoCD, Prometheus, Karpenter CRDs) inside the cluster once EKS is active.
3. **Dynamic IAM Authentication**: AWS EKS does not use static passwords. The `exec` block dynamically executes `aws eks get-token` under the hood to generate a short-lived IAM OAuth bearer token so Terraform can authenticate securely to your EKS API endpoint without storing static credentials.

---

### 🛠️ Why `gavinbunney/kubectl` Provider Is Used
- The standard `hashicorp/kubernetes` provider works well for basic built-in Kubernetes objects (`Deployment`, `Service`), but **fails when parsing raw multi-document YAML strings or Custom Resource Definitions (CRDs)** that are not known at compile time.
- The `gavinbunney/kubectl` provider allows Terraform to apply raw Kubernetes YAML manifests (such as Karpenter's `NodePool` and `EC2NodeClass` CRDs) directly via `kubectl_manifest` without requiring `kubectl` CLI to be installed on the host machine.

---

## ⚡ 2. Compute Management & Karpenter Deep-Dive

### 🚀 Why Karpenter Is Required
Standard Kubernetes **Cluster Autoscaler** works by resizing AWS Auto Scaling Groups (ASGs), which takes **2 to 5 minutes** to provision new EC2 nodes.

- **Karpenter**: An open-source, high-performance node autoscaler built by AWS. It bypasses Auto Scaling Groups completely, talks directly to the AWS EC2 API (`ec2:RunInstances`), and provisions optimal EC2 instances in **10 to 30 seconds**.
- **Just-In-Time Sizing**: Evaluates pending pod resource requests (CPU, RAM, GPU, Spot vs On-Demand) and selects the exact cheapest instance type across hundreds of EC2 SKUs.
- **Consolidation**: Automatically terminates empty or underutilized nodes and packs pods onto smaller nodes to save costs.

---

### 📩 Why the SQS Interruption Queue Exists
When using EC2 Spot Instances, AWS can reclaim nodes with a **2-minute Spot Interruption Warning** or **EC2 Rebalance Notification**.

```
AWS EC2 Event ➔ AWS EventBridge ➔ SQS Queue (karpenter-interruption) ➔ Karpenter Controller Pod ➔ Graceful Pod Eviction
```

1. AWS EventBridge catches Spot termination events and sends them to the `karpenter-interruption` SQS queue.
2. The Karpenter controller pod monitors this SQS queue.
3. Upon receiving an interruption notice, Karpenter immediately provisions a replacement node and **gracefully drains all pods off the target instance** *before* AWS terminates the node, guaranteeing **zero application downtime**.

---

## 📊 3. Pods & Addon Infrastructure

### 🔍 How Prometheus Stack Operates
Deployed via [`prometheus.tf`](file:///d:/Sundeep/projects/cloudnative-ai-ops/terraform/prometheus.tf) into the `monitoring` namespace as Kubernetes Pods:
- **Prometheus**: Runs as a `StatefulSet` Pod storing time-series metrics.
- **Grafana**: Runs as a `Deployment` Pod serving monitoring dashboards.
- **Node-Exporter**: Runs as a `DaemonSet` Pod (1 instance per worker node) collecting CPU, RAM, and disk hardware metrics.
- **AlertManager**: Runs as a `StatefulSet` Pod to send alert webhooks to our FastAPI AI Agent.

### 🐙 How ArgoCD Operates
Deployed via [`argocd.tf`](file:///d:/Sundeep/projects/cloudnative-ai-ops/terraform/argocd.tf) into the `argocd` namespace as Kubernetes Pods:
- **`argocd-server`**: REST/gRPC server exposing the UI and CLI endpoints.
- **`argocd-application-controller`**: Continuous reconciliation loop comparing Git repository state against live cluster state.
- **`argocd-repo-server`**: Maintains local clone of Git repositories and generates Kubernetes manifests.

---

## ⚙️ 4. Deployment Instructions

### 🟢 Ultra-Low Cost Configuration (`env/prd.tfvars`)
To reuse an existing AWS VPC and avoid creating new NAT Gateways or Load Balancers ($15 - $45 total for 2 weeks):

```hcl
aws_region          = "ap-south-1"
environment         = "prd"
cluster_name        = "kubeops-ai-prd-cluster"
cluster_version     = "1.30"

# Pass your existing VPC & Subnets:
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-01111111111111111", "subnet-02222222222222222"]
public_subnet_ids  = ["subnet-03333333333333333", "subnet-04444444444444444"]

node_instance_types = ["t3a.medium", "t3.medium"]
desired_node_count  = 2
min_node_count      = 1
max_node_count      = 3
enable_karpenter    = true
```

---

### 🚀 GitHub Actions CI/CD Triggering
The workflow in [`.github/workflows/terraform-deploy.yml`](file:///d:/Sundeep/projects/cloudnative-ai-ops/.github/workflows/terraform-deploy.yml) injects backend settings dynamically on trigger:

```yaml
terraform init -reconfigure \
  -backend-config="bucket=s3-arovita-${{ github.event.inputs.env }}-tf-bucket" \
  -backend-config="key=${{ github.event.inputs.env }}/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="use_lockfile=true"
```

1. Go to **Actions** tab in GitHub.
2. Select **Terraform Plan, Apply**.
3. Choose Environment: `prd` and Action: `plan` or `apply`.

---

### 💻 Local Terraform Commands
```bash
cd terraform

# 1. Initialize S3 Backend
terraform init -reconfigure \
  -backend-config="bucket=s3-arovita-prd-tf-bucket" \
  -backend-config="key=prd/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="use_lockfile=true"

# 2. Preview Plan
terraform plan -var-file=env/prd.tfvars

# 3. Apply Changes
terraform apply -auto-approve -var-file=env/prd.tfvars

# 4. Connect kubectl to EKS cluster
aws eks update-kubeconfig --region ap-south-1 --name kubeops-ai-prd-cluster
```
