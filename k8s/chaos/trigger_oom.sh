#!/usr/bin/env bash
# Injects Memory pressure causing OOMKilled (exit code 137)
set -e

NAMESPACE=${1:-default}
POD=$(kubectl get pods -n "$NAMESPACE" -l app=payment-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "payment-service")

echo "💥 Injecting memory leak into pod: $POD (namespace: $NAMESPACE)"
kubectl exec -n "$NAMESPACE" "$POD" -- python3 -c "
import bytearray
print('Allocating 600MB RAM...')
x = bytearray(600 * 1024 * 1024)
" 2>/dev/null || true

echo "✅ Chaos injected. Pod will experience OOMKilled and trigger Prometheus alert."
