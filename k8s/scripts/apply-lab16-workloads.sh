#!/usr/bin/env bash
# Applies demo StatefulSet and init-container examples (order matters for wait-for-service).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

kubectl apply -f "${ROOT}/demo-statefulset.yaml"
kubectl apply -f "${ROOT}/init-containers/02-wait-for-service-deps.yaml"
kubectl rollout status deployment/lab16-wait-demo -n default --timeout=120s
kubectl apply -f "${ROOT}/init-containers/03-wait-for-service-pod.yaml"
kubectl apply -f "${ROOT}/init-containers/01-init-download-pod.yaml"

echo "Workloads applied. Watch: kubectl get pods -w"
