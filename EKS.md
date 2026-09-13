# ☸️ AWS EKS Architecture & Worker Node Comparison Guide (EKS.md)

This document explains the architecture of **Amazon Elastic Kubernetes Service (EKS)**, the responsibility boundary between AWS and the customer, and a comprehensive comparison of all worker node provisioning models in Kubernetes on AWS.

---

## 🏛️ 1. AWS EKS High-Level Architecture

AWS EKS splits Kubernetes into two distinct operational layers:

```
+---------------------------------------------------------------------------------------------------+
| AWS MANAGED CONTROL PLANE (Fully Managed by AWS across 3 Availability Zones)                      |
|                                                                                                   |
|   +-------------------+    +--------------------+    +------------------+    +-----------------+  |
|   |  kube-apiserver   |    |  etcd Database     |    | kube-scheduler   |    | controller-mgr  |  |
|   |  (API Endpoint)   |    |  (State Storage)   |    | (Pod Scheduling) |    | (Reconciliation)|  |
|   +-------------------+    +--------------------+    +------------------+    +-----------------+  |
|                                                                                                   |
|   - Automatic Multi-AZ High Availability (SLA 99.95%)                                             |
|   - Automatic etcd Backups & Security Patching                                                    |
|   - Native IAM OIDC & VPC ENI Integration                                                         |
+---------------------------------------------------------------------------------------------------+
                                              |
                          Kubernetes API / VPC ENIs / Security Groups
                                              |
+---------------------------------------------------------------------------------------------------+
| DATA PLANE / WORKER NODES (Customer Managed / Provisioned)                                        |
|                                                                                                   |
|   +-----------------------------+  +-----------------------------+  +--------------------------+  |
|   | EKS Managed Node Groups     |  | Karpenter JIT Nodes         |  | AWS Fargate Serverless   |  |
|   | (System Bootstrap Workloads)|  | (Dynamic Pod Autoscaling)   |  | (Isolated Microservices) |  |
|   +-----------------------------+  +-----------------------------+  +--------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 🔒 2. EKS Control Plane: What AWS Manages

AWS provisions and manages the Kubernetes Control Plane in a dedicated AWS-managed VPC:

### What AWS Operates:
- **`kube-apiserver`**: High-availability API server load-balanced across 3 Availability Zones.
- **`etcd`**: Distributed key-value store replicated across 3 AZs with automated snapshots.
- **`kube-scheduler` & `kube-controller-manager`**: Core control loops.
- **Upgrades & Security Patches**: One-click Kubernetes version upgrades (1.29 ➔ 1.30 ➔ 1.31) with zero downtime for control plane APIs.

---

## 🚜 3. Worker Node Types on AWS EKS: Deep Comparison

There are **5 primary methods** to provision worker compute in AWS EKS. Here is how they compare:

---

### Option 1: EKS Managed Node Groups (MNG) — *Used in our Project*
AWS automatically provisions and manages Amazon EC2 instances backed by AWS Auto Scaling Groups (ASGs).

- **How it Works**: You define instance types (e.g. `t3.medium`), min/max/desired size, and AWS creates the ASG, applies EKS-optimized AMIs, and handles node drains during rolling upgrades.
- **Advantages (Pros)**:
  - **Ease of Use**: Fully supported by Terraform and AWS CLI out of the box.
  - **Automated Lifecycle**: One-click node AMI updates with graceful pod eviction (`kubectl drain`).
  - **Standard Reliability**: Works seamlessly with Cluster Autoscaler.
- **Disadvantages (Cons)**:
  - **Slower Scaling**: Scaling up a new node takes **2 to 5 minutes** (ASG spin-up + kubelet initialization).
  - **Rigid Instance Sizing**: Fixed EC2 instance sizes can lead to wasted CPU/RAM capacity.
- **Best Use Case**: Core system components, ingress controllers, background agents, and baseline workloads.

---

### Option 2: Karpenter Just-In-Time (JIT) Nodes — *Used in our Project*
An open-source, high-performance node autoscaler built by AWS that bypasses Auto Scaling Groups.

- **How it Works**: Karpenter evaluates pending/unschedulable pods, calculates exact resource requests (CPU, RAM, GPU, architecture, Spot vs On-Demand), and provisions optimal EC2 instances **directly via the AWS EC2 API** in 10–30 seconds.
- **Advantages (Pros)**:
  - **Ultra-Fast Scaling**: Launches instances in **10 to 30 seconds**.
  - **Maximum Cost Efficiency**: Automatically selects the cheapest Spot or On-Demand instance type across hundreds of EC2 SKUs.
  - **Automatic Consolidation**: Automatically terminates empty or underutilized nodes and packs pods onto smaller nodes.
  - **No ASGs Required**: Eliminates Auto Scaling Group complexity.
- **Disadvantages (Cons)**:
  - Requires initial IAM & Helm chart configuration.
  - Must manage NodePool and EC2NodeClass custom resources (CRDs).
- **Best Use Case**: Dynamic application pods, microservices, batch jobs, dynamic AI workloads, and cost-optimized Spot fleets.

---

### Option 3: AWS Fargate for EKS (Serverless Pods)
AWS Fargate runs each Kubernetes Pod in its own isolated compute environment.

- **How it Works**: AWS provisions an isolated micro-VM per pod. You don't manage underlying EC2 nodes or AMIs at all.
- **Advantages (Pros)**:
  - **Zero Node Management**: No OS patching, AMI updates, or EC2 instance sizing.
  - **Pod-Level Security Isolation**: Ideal for untrusted multi-tenant workloads.
- **Disadvantages (Cons)**:
  - **Higher Cost**: ~20% more expensive per vCPU/GB compared to On-Demand EC2.
  - **Limitations**: No DaemonSets allowed, no privileged containers, no EBS persistent volume attachments.
- **Best Use Case**: Low-frequency background jobs, event-driven microservices, or environments requiring hard isolation.

---

## 📊 Summary Comparison Matrix

| Feature | Self-Managed EC2 | EKS Managed Node Groups (MNG) | Karpenter JIT Nodes | AWS Fargate | EKS Auto Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Provisioning Speed** | 3 - 5 mins | 2 - 5 mins | ⚡ **10 - 30 secs** | 1 - 2 mins | 30 - 60 secs |
| **Management Overhead** | High | Low | Low | **Zero** | **Zero** |
| **Spot Instance Support** | Manual | Good | ⚡ **Best-in-class** | No | Automated |
| **Cost Efficiency** | Medium | Medium | ⚡ **Highest** | Low | High |
| **DaemonSet Support** | Yes | Yes | Yes | **No** | Yes |
| **EBS Volume Support** | Yes | Yes | Yes | Limited | Yes |

---

## 🎯 4. What We Are Implementing in This Repository

In our **KubeOps-Aegis** infrastructure, we use a hybrid **Production Best-Practice Architecture**:

1. **Bootstrap Managed Node Group (`bootstrap-worker-group`)**:
   - Runs **2 x `t3a.medium`** instances in private subnets.
   - Hosts essential infrastructure components: **CoreDNS**, **ArgoCD**, **Kube-Prometheus-Stack**, and the **Karpenter Controller**.

2. **Karpenter Autoscaling (`default` NodePool)**:
   - Watches for dynamic application workloads (`payment-service` microservice, AI-Ops Agent tasks).
   - Dynamically launches Spot and On-Demand EC2 instances (`c5`, `m5`, `t3`) on demand and consolidates them when idle.
