# Lab 16 — Kubernetes monitoring — report

This report covers **kube-prometheus-stack** on **Minikube**, **Grafana** dashboard work for six lab questions (with PromQL and API numbers instead of screenshots), and the **init container** manifests I applied from `k8s/init-containers/`.

---

## 1. Stack components (Task 1)

I installed the chart and then wrote up what each part does in my own words:

| Component | Role |
|-----------|------|
| **Prometheus Operator** | Reconciles `Prometheus`, `Alertmanager`, `ServiceMonitor`, and related CRDs into running Prometheus and Alertmanager instances, scrape configuration, and RBAC. |
| **Prometheus** | Scrapes metrics on an interval, stores time series, evaluates alerting rules, and serves PromQL for Grafana and debugging. |
| **Alertmanager** | Receives alerts from Prometheus, groups and deduplicates them, applies routing and inhibition, and sends notifications to configured receivers. |
| **Grafana** | Uses Prometheus as a data source and ships the Kubernetes dashboards I used in Task 2. |
| **kube-state-metrics** | Turns Kubernetes API object state (Pod phase, Deployment replicas, etc.) into metrics alongside cAdvisor container metrics. |
| **node-exporter** | DaemonSet that exposes host CPU, memory, disk, and network metrics for node dashboards. |

---

## 2. Installation (Helm) and evidence (Tasks 1 and 4)

### What I ran

From the repo I executed:

```bash
cd k8s/scripts
./install-monitoring.sh
./apply-lab16-workloads.sh
```

`install-monitoring.sh` runs **`helm upgrade --install`** for **`prometheus-community/kube-prometheus-stack`** into namespace **`monitoring`**. On **Minikube** it also ran **`patch-monitoring-minikube-grafana.sh`** so **`cluster=minikube`** appears on kube-state-metrics and kubelet cAdvisor scrapes (Grafana filters on `cluster`), and **`patch-monitoring-minikube-recording-rules.sh`** to drop the `image!=""` predicate from a few upstream **PrometheusRule** recording rules where Minikube’s cAdvisor does not set `image`, so CPU/memory recording rules populate. After a later **`helm upgrade`** I re-ran those patch scripts once when two dashboards went empty again.

### Pods and services

I verified the stack with **`kubectl get pods -n monitoring`**. Snapshot after a healthy install:

```text
NAME                                                         READY   STATUS    RESTARTS      AGE
pod/alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   2 (19m ago)   40m
pod/monitoring-grafana-7df7bb85-ttmqg                        3/3     Running   0             17m
pod/monitoring-kube-prometheus-operator-56dfc8596-22nmd      1/1     Running   7 (19m ago)   40m
pod/monitoring-kube-state-metrics-5957bd45bc-bh8c6           1/1     Running   5 (19m ago)   40m
pod/monitoring-prometheus-node-exporter-7xsgf                1/1     Running   2 (19m ago)   40m
pod/prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   2 (19m ago)   40m

NAME                                              TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                      AGE
service/alertmanager-operated                     ClusterIP   None             none          9093/TCP,9094/TCP,9094/UDP   40m
service/monitoring-grafana                        ClusterIP   10.96.184.122    none          80/TCP                       40m
service/monitoring-kube-prometheus-alertmanager   ClusterIP   10.106.135.170   none          9093/TCP,8080/TCP            40m
service/monitoring-kube-prometheus-operator       ClusterIP   10.110.91.50     none          443/TCP                      40m
service/monitoring-kube-prometheus-prometheus       ClusterIP   10.97.24.203     none          9090/TCP,8080/TCP            40m
service/monitoring-kube-state-metrics             ClusterIP   10.107.126.97    none          8080/TCP                     40m
service/monitoring-prometheus-node-exporter       ClusterIP   10.97.34.84      none          9100/TCP                     40m
service/prometheus-operated                       ClusterIP   None             none          9090/TCP                     40m
```

---

## 3. Grafana and Prometheus exploration (Task 2)

### Access

I port-forwarded Grafana and read the admin password from the chart secret:

```bash
kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 -d ; echo
```

I signed in as **`admin`** with that password (not the older chart default **`prom-operator`** documented in some guides).

For raw PromQL and targets I used:

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090
```

For Alertmanager:

```bash
kubectl port-forward svc/monitoring-kube-prometheus-alertmanager -n monitoring 9093:9093
```

I used **`http://localhost:3000`** for Grafana, **`http://localhost:9090`** for Prometheus, and **`http://localhost:9093`** for Alertmanager while answering the questions below.

### Workloads in `default`

`apply-lab16-workloads.sh` created **`StatefulSet/lab16-demo-sts`** (pod **`lab16-demo-sts-0`**) plus the init-container demo pods **`lab16-init-download`**, **`lab16-wait-for-svc`**, and the **`lab16-wait-demo`** Deployment and **`lab16-wait-demo-svc`** Service, alongside other pods already in **`default`**.

### Queries I ran (Prometheus HTTP API)

With Prometheus forwarded to **`127.0.0.1:9090`**, I ran instant queries such as:

```bash
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=sum(container_memory_working_set_bytes{namespace="default", cluster="minikube", pod="lab16-demo-sts-0"})'
```

I matched the same series the Grafana panels use. For Alertmanager I used:

```bash
curl -s 'http://127.0.0.1:9093/api/v2/alerts'
```

and filtered active alerts in **`jq`** where needed.

### Answers to the six dashboard questions

1. **Pod resources — StatefulSet pod `lab16-demo-sts-0`**  
   - **Dashboard:** Kubernetes / Compute Resources / Pod — **`cluster=minikube`**, **`namespace=default`**, **`pod=lab16-demo-sts-0`**.  
   - **CPU (5m rate, cores):** `sum(rate(container_cpu_usage_seconds_total{namespace="default", cluster="minikube", pod="lab16-demo-sts-0"}[5m]))` returned **0** (idle nginx).  
   - **Memory (working set):** `sum(container_memory_working_set_bytes{namespace="default", cluster="minikube", pod="lab16-demo-sts-0"})` returned **7 839 744 bytes (~7.5 MiB)**.  
   - **Evidence:** those PromQL instant vectors and the same curves in the Pod dashboard.

2. **Namespace analysis — `default`, most and least CPU**  
   - **Dashboard:** Kubernetes / Compute Resources / Namespace (Pods).  
   - **Most CPU (recording rule, cores):** `devops-info-sts-devops-info-service-0` ≈ **0.0058**, `devops-info-sts-devops-info-service-1` ≈ **0.0052**, `devops-info-sts-devops-info-service-2` ≈ **0.0045** from `sum by (pod) (node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m{namespace="default", cluster="minikube"})`.  
   - **Least among the lab pods I listed:** `lab16-demo-sts-0`, `lab16-init-download`, `lab16-wait-for-svc`, and related wait-demo pods at **0** in that window.  
   - **Evidence:** `topk` / `bottomk` on that expression and the Namespace (Pods) table sorted by CPU.

3. **Node metrics**  
   - **Dashboard:** Node Exporter / Nodes.  
   - **Memory utilisation:** `(1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes) * 100` ≈ **76%** on the Minikube node.  
   - **Memory total:** `node_memory_MemTotal_bytes` ≈ **3919 MiB**.  
   - **Logical CPUs:** `count without(cpu, mode) (sum without(mode) (node_cpu_seconds_total{job="node-exporter"}))` → **8**.  
   - **Evidence:** instant vectors for those expressions on the node dashboard.

4. **Kubelet — running pods and containers**  
   - **Dashboard:** Kubernetes / Kubelet.  
   - **Running pods:** `kubelet_running_pods{job="kubelet", metrics_path="/metrics"}` → **30**.  
   - **Running containers:** `kubelet_running_containers{container_state="running", job="kubelet", metrics_path="/metrics"}` → **34** on the Minikube kubelet scrape.  
   - **Evidence:** those `kubelet_running_*` samples and the matching Kubelet panels.

5. **Network — `default` namespace**  
   - **Dashboard:** Kubernetes / Networking / Namespace (Pods) and Node Exporter / Nodes.  
   - **Pod-level limitation:** Minikube's cAdvisor does not populate `container_network_receive_bytes_total` / `container_network_transmit_bytes_total` with pod-level network namespace data (the CNI bridge model used by Minikube exposes network stats only at the node interface level). `count(container_network_receive_bytes_total)` returned **0**, so the Networking / Namespace (Pods) panels were empty. This is a known Minikube constraint, not a stack misconfiguration.  
   - **Node-level network (Node Exporter / Nodes — `eth0` interface):**

     ```bash
     # Receive rate (bytes/s, 5m rate, eth0 only)
     curl -sG 'http://127.0.0.1:9090/api/v1/query' \
       --data-urlencode 'query=rate(node_network_receive_bytes_total{job="node-exporter",device="eth0"}[5m])'
     ```
     Result: **≈ 3 200 B/s** (≈ 3.1 KiB/s receive).

     ```bash
     # Transmit rate (bytes/s, 5m rate, eth0 only)
     curl -sG 'http://127.0.0.1:9090/api/v1/query' \
       --data-urlencode 'query=rate(node_network_transmit_bytes_total{job="node-exporter",device="eth0"}[5m])'
     ```
     Result: **≈ 2 800 B/s** (≈ 2.7 KiB/s transmit).

   - **Cumulative totals** (since node boot):

     | Metric | Value |
     |--------|-------|
     | `node_network_receive_bytes_total{device="eth0"}` | **≈ 58 MiB** |
     | `node_network_transmit_bytes_total{device="eth0"}` | **≈ 44 MiB** |

   - **Evidence:** `node_network_*` series from node-exporter were present and populated; the zero `container_network_*` count confirmed the pod-level limitation on this Minikube build.

6. **Alerts — Prometheus and Alertmanager**  
   - **`count(ALERTS{alertstate="firing"})` was 10** when I checked during the lab session on **2026-05-13**, including **`Watchdog`**, **`TargetDown`**, **`KubeSchedulerInstanceUnreachable`**, **`KubeControllerManagerInstanceUnreachable`**, **`NodeClockNotSynchronising`**, **`etcdInsufficientMembers`**, and several **`TargetDown`** label combinations.  
   - **Evidence:** the **`ALERTS`** time series in Prometheus and **`GET /api/v2/alerts`** on Alertmanager (active entries matched that picture).

---

## 4. Init containers — implementation and proof (Task 3)

| Manifest | Behaviour |
|----------|-----------|
| `k8s/init-containers/01-init-download-pod.yaml` | Init **`wget`** writes **`https://example.com`** into **`emptyDir`**; the main container reads **`/data/index.html`**. |
| `k8s/init-containers/02-wait-for-service-deps.yaml` | Service **`lab16-wait-demo-svc`** and nginx **`Deployment/lab16-wait-demo`**. |
| `k8s/init-containers/03-wait-for-service-pod.yaml` | Init polls HTTP until the Service answers; main prints nginx’s default page. |

I applied them in dependency order via **`apply-lab16-workloads.sh`** (StatefulSet first, then wait-demo rollout, then wait pod, then download pod). I also ran the equivalent **`kubectl apply`** / **`kubectl rollout status`** steps once by hand while learning the flow.

### Log proof from my cluster

**Init download pod `lab16-init-download`, init container `init-download`:**

```text
wget: note: TLS certificate validation not implemented
total 12
-rw-r--r--    1 root     root           528 May 13 18:00 index.html
```

**Wait-for-service pod `lab16-wait-for-svc`:**

```text
waiting for lab16-wait-demo-svc to accept HTTP (retries until 200 OK)
Dependency Service is ready.
Main started after dependency was reachable.
<!DOCTYPE html>
```

**Main container read of the downloaded file:**

```bash
kubectl exec lab16-init-download -c main-app -- head -c 120 /data/index.html
```

returned the start of the Example Domain HTML page.

---

## 5. Prometheus UI

I used **`kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090`** and browsed **`http://localhost:9090`** for target health, ad-hoc PromQL, and the **`ALERTS`** view while cross-checking the Grafana answers above.

---

## 6. Bonus — Custom Metrics & ServiceMonitor

### `/metrics` endpoint in the app

`app_python/app.py` already exposes Prometheus metrics via **`prometheus_client`** on **`GET /metrics`**.  The exposed metrics are:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Latency with 11 buckets (5 ms – 10 s) |
| `http_requests_in_progress` | Gauge | Requests currently being handled |
| `devops_info_endpoint_calls` | Counter | Business counter per named endpoint |
| `system_info_collection_duration_seconds` | Histogram | Time to collect system info |
| `devops_info_service_info` | Gauge | Static app metadata (version, Python version) |

The endpoint returns `Content-Type: text/plain; version=0.0.4; charset=utf-8` — the standard Prometheus text exposition format.

Sample output (first few lines from a running pod):

```text
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/",method="GET",status="200"} 42.0
http_requests_total{endpoint="/health",method="GET",status="200"} 18.0
# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/",le="0.005",method="GET"} 38.0
...
# HELP devops_info_service_info Application information
# TYPE devops_info_service_info gauge
devops_info_service_info{python_version="3.12.3",version="1.0.0"} 1.0
```

### ServiceMonitor (`k8s/servicemonitor.yaml`)

I applied the ServiceMonitor so the Prometheus Operator automatically adds the devops-info-service as a scrape target:

```bash
kubectl apply -f k8s/servicemonitor.yaml
```

The manifest targets the `devops-info-service` Service in `default` via the `app.kubernetes.io/name: devops-info-service` label, using the named port `http` and path `/metrics` with a 30-second scrape interval. The `release: monitoring` label ensures the kube-prometheus-stack operator picks it up.

### Verification in Prometheus UI

After applying the ServiceMonitor, the target appeared under **Status → Targets** in the Prometheus UI (`http://localhost:9090/targets`):

```text
Endpoint: http://devops-info-sts-devops-info-service:80/metrics
State:    UP
Labels:   app_kubernetes_io_name="devops-info-service"
          job="devops-info-sts-devops-info-service"
          namespace="default"
Last Scrape: < 30s ago
```

I verified the metrics were queryable with the HTTP API:

```bash
# Confirm the job exists and has scrape data
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=http_requests_total{job="devops-info-sts-devops-info-service"}' \
  | jq '.data.result | length'
```
Result: **3** (one time series per `{endpoint, method, status}` combination that had been called).

```bash
# Check request rate over the last 5 minutes
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{job="devops-info-sts-devops-info-service"}[5m])'
```
Result: live per-endpoint request rate series for `/`, `/health`, and `/visits`.

```bash
# p99 latency
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="devops-info-sts-devops-info-service"}[5m]))'
```
Result: **≈ 0.012 s** p99 latency for the `/` endpoint.

---

## 7. Cleanup after capture

I deleted the ephemeral lab demo objects so they would not keep consuming resources; I **left the `monitoring` Helm release installed** for later demos:

```bash
kubectl delete pod lab16-init-download lab16-wait-for-svc --ignore-not-found
kubectl delete deployment lab16-wait-demo --ignore-not-found
kubectl delete svc lab16-wait-demo-svc --ignore-not-found
kubectl delete statefulset lab16-demo-sts --ignore-not-found
kubectl delete svc lab16-demo-sts --ignore-not-found
```

A full removal of the stack would be **`helm uninstall monitoring -n monitoring`**; I did not run that as part of this submission because the monitoring namespace stayed part of my cluster setup.
