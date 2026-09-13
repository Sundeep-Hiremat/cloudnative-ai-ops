#!/usr/bin/env bash
# Injects CPU stress causing CPU Throttling
set -e

NAMESPACE=${1:-default}
POD=$(kubectl get pods -n "$NAMESPACE" -l app=payment-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "payment-service")

echo "🔥 Injecting CPU load into pod: $POD (namespace: $NAMESPACE)"
kubectl exec -n "$NAMESPACE" "$POD" -- python3 -c "
import time
start = time.time()
while time.time() - start < 120:
    _ = [x**2 for x in range(1000000)]
" 2>/dev/null || true

echo "✅ CPU stress injected."
