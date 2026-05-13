#!/usr/bin/env bash
# Minikube kubelet/cAdvisor often omits the `image` label. Upstream kubernetes-mixin
# recording rules filter on `image!=""`, which excludes all samples. Strip that
# selector from the bundled PrometheusRules in `monitoring` (safe on this lab cluster).
set -euo pipefail

RULES=(
  monitoring-kube-prometheus-k8s.rules.container-cpu-usage-second
  monitoring-kube-prometheus-k8s.rules.container-memory-cache
  monitoring-kube-prometheus-k8s.rules.container-memory-rss
  monitoring-kube-prometheus-k8s.rules.container-memory-swap
  monitoring-kube-prometheus-k8s.rules.container-memory-working-s
)

for r in "${RULES[@]}"; do
  kubectl get prometheusrule "$r" -n monitoring -o yaml | sed 's/, image!=""//g' | kubectl apply -f -
done

echo "PrometheusRules patched. Wait ~60s for rule evaluation."
