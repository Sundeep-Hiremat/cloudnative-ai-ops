# Setup Local Kubernetes (Kind) Cluster with ArgoCD and Monitoring
Write-Host "🚀 Creating local Kind cluster 'kubeops-cluster'..." -ForegroundColor Cyan

$clusterConfig = @"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 8080
    protocol: TCP
  - containerPort: 30443
    hostPort: 8443
    protocol: TCP
- role: worker
- role: worker
"@

$clusterConfig | kind create cluster --name kubeops-cluster --config=-

Write-Host "📦 Installing ArgoCD..." -ForegroundColor Cyan
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

Write-Host "📊 Installing Prometheus CRDs & AlertManager..." -ForegroundColor Cyan
kubectl create namespace monitoring
kubectl apply -f ../k8s/monitoring/prometheus-alerts.yaml
kubectl apply -f ../gitops/argocd/application.yaml

Write-Host "✅ Local Kind Cluster is ready for Autonomous AI-Ops demos!" -ForegroundColor Green
