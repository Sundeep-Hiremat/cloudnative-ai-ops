# ⚡ KubeOps-Aegis AWS EKS Infrastructure & Deployment Guide

This directory contains the production Infrastructure-as-Code (IaC) for **KubeOps-Aegis**, built using **Terraform**, **AWS EKS**, **Karpenter Just-In-Time Autoscaling**, **ArgoCD**, and **Prometheus Stack**.

---

## 🏛️ Infrastructure Architecture

```
+-----------------------------------------------------------------------------------------------+
| AWS VPC (ap-south-1)                                                                          |
|                                                                                               |
|  +-------------------------------------+   +-----------------------------------------------+  |
|  | Public Subnet 1 & 2                 |   | Private Subnet 1 & 2                          |  |
|  | - Internet Gateway (IGW)             |   | - EKS Control Plane ENIs (EKS 1.30)           |  |
|  | - NAT Gateway                       |   | - Bootstrap Managed Node Group (t3.medium)    |  |
|  | - Ingress ALBs                      |   | - Karpenter Autoscaled EC2 Nodes (Spot/OnDem) |  |
|  +-------------------------------------+   +-----------------------------------------------+  |
+-----------------------------------------------------------------------------------------------+
```

---

## 💡 Compute Management: EKS Managed Nodes vs Karpenter vs Auto Mode

| Compute Option | Provisioning Mechanism | Scaling Speed | Cost Optimization | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Managed Node Groups (MNG)** | AWS Auto Scaling Groups (ASG) | 2–5 minutes | Pre-sized instance lists | System core workloads (CoreDNS, ArgoCD, Karpenter) |
| **Karpenter Autoscaling** | Direct EC2 `RunInstances` API | 10–30 seconds | Dynamic Spot & On-Demand consolidation | Dynamic application workloads & microservices |
| **EKS Auto Mode** | Fully AWS-managed compute driver | Automated | AWS-managed optimization | Zero-node-management serverless Kubernetes |

In this architecture, **Managed Node Groups** handle initial bootstrap nodes (running ArgoCD, Karpenter Controller, and Prometheus), while **Karpenter** handles rapid scaling of application workloads.

---

## ⚙️ Configuration Parameters (`env/prd.tfvars`)

### 1. Default Setup (Creates VPC Module Automatically)
```hcl
aws_region          = "ap-south-1"
environment         = "prd"
cluster_name        = "kubeops-ai-prd-cluster"
cluster_version     = "1.30"
vpc_cidr            = "10.0.0.0/16"
node_instance_types = ["t3.medium", "t3a.medium"]
desired_node_count  = 3
min_node_count      = 2
max_node_count      = 6
enable_karpenter    = true
```

### 2. Custom Existing VPC Integration
If you already have a VPC with 2 public subnets and 2 private subnets, simply uncomment and populate the variables in [`env/prd.tfvars`](file:///d:/Sundeep/projects/cloudnative-ai-ops/terraform/env/prd.tfvars):

```hcl
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-01111111111111111", "subnet-02222222222222222"]
public_subnet_ids  = ["subnet-03333333333333333", "subnet-04444444444444444"]
```

---

## 🚀 GitHub Actions Dynamic S3 CI/CD Deployment

The workflow located in [`.github/workflows/terraform-deploy.yml`](file:///d:/Sundeep/projects/cloudnative-ai-ops/.github/workflows/terraform-deploy.yml) injects backend settings dynamically on trigger:

```yaml
terraform init -reconfigure \
  -backend-config="bucket=s3-arovita-${{ github.event.inputs.env }}-tf-bucket" \
  -backend-config="key=${{ github.event.inputs.env }}/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="use_lockfile=true"
```

### Triggering via GitHub Actions:
1. Go to **Actions** tab in GitHub repository.
2. Select **Terraform Plan, Apply**.
3. Choose Environment: `prd`.
4. Choose Action: `plan` (preview changes) or `apply` (provision infrastructure).
5. Click **Run workflow**.

---

## 💻 Manual / Local Deployment

To run Terraform locally (using AWS CLI credentials):

```bash
cd terraform

# 1. Initialize with your target S3 bucket
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

---

## 📦 Installed Helm Releases

1. **ArgoCD**: Deployed into `argocd` namespace (Insecure mode / LoadBalancer service enabled).
2. **Kube-Prometheus-Stack**: Deployed into `monitoring` namespace (AlertManager + Prometheus).
3. **Karpenter**: Deployed into `karpenter` namespace with SQS Interruption Queue and default `NodePool` & `EC2NodeClass`.
