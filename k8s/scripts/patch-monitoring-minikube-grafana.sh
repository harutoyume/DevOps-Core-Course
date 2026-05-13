#!/usr/bin/env bash
# After `helm install` kube-prometheus-stack on **Minikube**, run this so
# Grafana kubernetes-mixin dashboards match series: add `cluster=minikube` on
# kube-state-metrics and kubelet/cAdvisor scrapes, then relax upstream
# recording rules that filter on `image!=""` (often missing on Minikube cAdvisor).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

kubectl patch servicemonitor monitoring-kube-state-metrics -n monitoring --type=json -p='[
  {"op":"add","path":"/spec/endpoints/0/metricRelabelings","value":[
    {"action":"replace","targetLabel":"cluster","replacement":"minikube"}
  ]}
]' 2>/dev/null || kubectl patch servicemonitor monitoring-kube-state-metrics -n monitoring --type=json -p='[
  {"op":"add","path":"/spec/endpoints/0/metricRelabelings/-","value":{
    "action":"replace","targetLabel":"cluster","replacement":"minikube"
  }}
]' || true

kubectl patch servicemonitor monitoring-kube-prometheus-kubelet -n monitoring --type=json -p='[
  {"op":"add","path":"/spec/endpoints/1/metricRelabelings/-","value":{
    "action":"replace","targetLabel":"cluster","replacement":"minikube"
  }}
]' 2>/dev/null || true

if [[ -x "$ROOT/patch-monitoring-minikube-recording-rules.sh" ]]; then
  "$ROOT/patch-monitoring-minikube-recording-rules.sh" || true
fi

echo "Wait ~90s for Prometheus scrapes and recording rules before opening Grafana."
