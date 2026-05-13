#!/usr/bin/env bash
# Lab 16 — Task 1: Install kube-prometheus-stack into namespace `monitoring`.
# On Minikube, also applies small compatibility patches so Grafana dashboards show data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --wait \
  --timeout 25m

if minikube status >/dev/null 2>&1; then
  echo "Minikube detected — applying Grafana / PrometheusRule compatibility patches."
  "$ROOT/patch-monitoring-minikube-grafana.sh" || true
fi

echo "Done. Check: kubectl get pods -n monitoring"
