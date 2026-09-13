#!/usr/bin/env bash
# Injects invalid environment variable causing CrashLoopBackOff
set -e

NAMESPACE=${1:-default}
echo "🔄 Injecting CrashLoopBackOff into payment-service deployment in namespace: $NAMESPACE"
kubectl set env deployment/payment-service -n "$NAMESPACE" FAIL_STARTUP=true DB_PASSWORD- 2>/dev/null || true
echo "✅ CrashLoopBackOff injected."
