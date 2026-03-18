# Lab 8 — Metrics & Monitoring with Prometheus

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  app-python  │     │  Prometheus  │     │   Grafana    │
│  (Flask App) │────▶│  (Metrics)   │────▶│ (Dashboard)  │
│  :8000→5000  │     │    :9090     │     │    :3000     │
│   /metrics   │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
        │                   ├──── scrapes ──▶ Loki (:3100)
        │                   └──── scrapes ──▶ Grafana (:3000)
        │
        ▼
┌──────────────┐     ┌──────────────┐
│   Promtail   │────▶│     Loki     │
│ (Log Shipper)│     │ (Log Storage)│
└──────────────┘     └──────────────┘
```

**Metric Flow:**

1. **app-python** exposes `/metrics` endpoint with Prometheus format metrics
2. **Prometheus** scrapes metrics from app, Loki, Grafana every 15 seconds
3. **Prometheus** stores time-series data with 15-day retention
4. **Grafana** queries Prometheus to visualize metrics in dashboards

All services communicate over a shared Docker `logging` bridge network.

---

## Application Instrumentation

### Metrics Added

The Python application (`app_python/app.py`) has been instrumented with the following Prometheus metrics:

#### HTTP Metrics (RED Method)

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `http_requests_total` | Counter | method, endpoint, status | Total HTTP requests (Rate) |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency distribution (Duration) |
| `http_requests_in_progress` | Gauge | - | Current concurrent requests |

#### Application-Specific Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `devops_info_endpoint_calls` | Counter | endpoint | Business metric - tracks endpoint usage |
| `system_info_collection_duration_seconds` | Histogram | - | Time to collect system information |
| `devops_info_service_info` | Gauge | version, python_version | Application metadata |

### Why These Metrics

**RED Method Implementation:**
- **R**ate (`http_requests_total`): Tracks requests per second per endpoint
- **E**rrors (`http_requests_total{status=~"5.."}}`): Filters for 5xx errors
- **D**uration (`http_request_duration_seconds`): Response time distribution with percentiles

**Label Strategy:**
- Endpoint normalization keeps cardinality low (`/`, `/health`, `/metrics`, `/other`)
- Status codes allow error rate calculation
- Method labels distinguish GET/POST/etc

### Code Changes

**requirements.txt:**
```txt
prometheus-client==0.23.1
```

**Key instrumentation code:**
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_request_duration_seconds = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
http_requests_in_progress = Gauge('http_requests_in_progress', 'HTTP requests currently being processed')

# Expose metrics endpoint
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
```

---

## Prometheus Configuration

### Scrape Configuration

**File:** `monitoring/prometheus/prometheus.yml`

| Job | Target | Path | Purpose |
|-----|--------|------|---------|
| `prometheus` | localhost:9090 | /metrics | Self-monitoring |
| `app` | app-python:5000 | /metrics | Application metrics |
| `loki` | loki:3100 | /metrics | Log storage metrics |
| `grafana` | grafana:3000 | /metrics | Dashboard metrics |

### Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| Scrape Interval | 15s | How often to collect metrics |
| Evaluation Interval | 15s | How often to evaluate rules |
| Retention Time | 15 days | How long to keep data |
| Retention Size | 10GB | Maximum storage size |

### Docker Compose Configuration

```yaml
prometheus:
  image: prom/prometheus:v3.0.0
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.retention.time=15d'
    - '--storage.tsdb.retention.size=10GB'
```

---

## Dashboard Walkthrough

### Application Metrics Dashboard

**8 panels implementing RED method and business metrics:**

#### 1. Request Rate (RED - Rate)
- **Query:** `sum(rate(http_requests_total[5m])) by (endpoint)`
- **Purpose:** Shows requests per second grouped by endpoint
- **Type:** Time series graph

#### 2. Error Rate (RED - Errors)
- **Query:** `sum(rate(http_requests_total{status=~"5.."}[5m]))`
- **Purpose:** Shows 5xx and 4xx errors per second
- **Type:** Time series graph

#### 3. Request Duration p95/p50 (RED - Duration)
- **Query:** `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))`
- **Purpose:** Shows 95th and 50th percentile latency
- **Type:** Time series graph

#### 4. Status Code Distribution
- **Query:** `sum by (status) (increase(http_requests_total[1h]))`
- **Purpose:** Pie chart showing distribution of 2xx/4xx/5xx responses
- **Type:** Pie chart

#### 5. Active Requests
- **Query:** `http_requests_in_progress`
- **Purpose:** Current number of in-flight requests
- **Type:** Stat panel

#### 6. Application Uptime
- **Query:** `up{job="app"}`
- **Purpose:** Shows if service is UP (1) or DOWN (0)
- **Type:** Stat panel with value mapping

#### 7. Business Metrics - Endpoint Calls
- **Query:** `sum(rate(devops_info_endpoint_calls[5m])) by (endpoint)`
- **Purpose:** Application-specific endpoint usage tracking
- **Type:** Time series graph

#### 8. Request Duration Heatmap
- **Query:** `sum(rate(http_request_duration_seconds_bucket[5m])) by (le)`
- **Purpose:** Visualizes latency distribution over time
- **Type:** Heatmap

---

## PromQL Examples

### 1. Request Rate per Endpoint
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```
Shows requests/second grouped by endpoint over 5-minute window.

### 2. Error Rate Percentage
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```
Calculates percentage of requests that result in 5xx errors.

### 3. 95th Percentile Latency
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```
Shows the latency below which 95% of requests complete.

### 4. Average Request Duration
```promql
sum(rate(http_request_duration_seconds_sum[5m])) / sum(rate(http_request_duration_seconds_count[5m]))
```
Calculates mean request duration over 5-minute window.

### 5. Services Down Alert Query
```promql
up == 0
```
Returns all targets that are currently down.

### 6. Request Rate by Method and Status
```promql
sum by (method, status) (rate(http_requests_total[5m]))
```
Breaks down traffic by HTTP method and response status.

### 7. Top Endpoints by Request Count
```promql
topk(5, sum by (endpoint) (increase(http_requests_total[1h])))
```
Shows the 5 most requested endpoints in the last hour.

---

## Production Setup

### Health Checks

All services have Docker health checks configured:

| Service | Health Check | Interval | Timeout |
|---------|--------------|----------|---------|
| Prometheus | `wget http://localhost:9090/-/healthy` | 10s | 5s |
| Grafana | `wget http://localhost:3000/api/health` | 10s | 5s |
| Loki | `wget http://localhost:3100/ready` | 10s | 5s |
| app-python | `python urllib.request http://localhost:5000/health` | 10s | 5s |

### Resource Limits

| Service | Memory Limit | CPU Limit | Memory Reserved | CPU Reserved |
|---------|--------------|-----------|-----------------|--------------|
| Prometheus | 1G | 1.0 | 256M | 0.25 |
| Grafana | 512M | 0.5 | 256M | 0.25 |
| Loki | 1G | 1.0 | 256M | 0.25 |
| Promtail | 512M | 0.5 | 128M | 0.1 |
| app-python | 256M | 0.5 | 128M | 0.1 |

### Data Retention Policies

| Service | Retention | Size Limit | Purpose |
|---------|-----------|------------|---------|
| Prometheus | 15 days | 10GB | Metric history |
| Loki | 7 days | N/A | Log history |

### Persistent Volumes

```yaml
volumes:
  prometheus-data:  # /prometheus - metric storage
  loki-data:        # /loki - log storage
  grafana-data:     # /var/lib/grafana - dashboards, users
```

**Testing Persistence:**
1. Create/modify dashboard
2. `docker compose down`
3. `docker compose up -d`
4. Verify data persists

---

## Testing Results

### 1. Services Status

```bash
$ docker compose ps
NAME         IMAGE                                 SERVICE      STATUS                    PORTS
app-python   haruyume/devops-info-service:latest   app-python   Up 6 minutes (healthy)    0.0.0.0:8000->5000/tcp
grafana      grafana/grafana:12.3.1                grafana      Up 7 minutes (healthy)    0.0.0.0:3000->3000/tcp
loki         grafana/loki:3.0.0                    loki         Up 16 minutes (healthy)   0.0.0.0:3100->3100/tcp
prometheus   prom/prometheus:v3.0.0                prometheus   Up 16 minutes (healthy)   0.0.0.0:9090->9090/tcp
promtail     grafana/promtail:3.0.0                promtail     Up 7 minutes
```

All services running with health checks passing.

### 2. Prometheus Targets

All 4 targets are UP and being scraped successfully:
- `app`: up (app-python:5000)
- `grafana`: up (grafana:3000)
- `loki`: up (loki:3100)
- `prometheus`: up (localhost:9090)

### 3. Application Metrics Output

```bash
$ curl http://localhost:8000/metrics | grep -E "^(http_requests_total|http_requests_in_progress|devops_info)"

# Request counters by endpoint and status
http_requests_total{endpoint="/health",method="GET",status="200"} 70.0
http_requests_total{endpoint="/",method="GET",status="200"} 103.0
http_requests_total{endpoint="/other",method="GET",status="404"} 10.0

# In-progress gauge
http_requests_in_progress 0.0

# Business metrics
devops_info_endpoint_calls_total{endpoint="/health"} 70.0
devops_info_endpoint_calls_total{endpoint="/"} 103.0
devops_info_service_info{python_version="3.13.12",version="1.0.0"} 1.0
```

### 4. Screenshots

- `prometheus-targets.png` - All Prometheus targets showing UP status
- `grafana-dashboard.png` - Application metrics dashboard with live data

---

## Metrics vs Logs: When to Use Each

| Aspect | Metrics (Prometheus) | Logs (Loki) |
|--------|---------------------|-------------|
| **Use Case** | Aggregated numerical data | Detailed event records |
| **Query** | "How many requests/sec?" | "What happened at 10:15?" |
| **Alerting** | Rate thresholds, SLOs | Pattern matching, errors |
| **Cardinality** | Low (labels) | High (full text) |
| **Storage** | Efficient (numeric) | Larger (text) |
| **Examples** | Request rate, latency p95 | Stack traces, debug info |

**Combined Observability:**
- Use metrics for dashboards and alerts
- Use logs for debugging and forensics
- Correlate using timestamps and request IDs

---

## Challenges & Solutions

### Challenge 1: Metrics Endpoint Self-Reference
**Problem:** `/metrics` endpoint was being instrumented, causing recursive metrics.
**Solution:** Skip metrics collection for `/metrics` endpoint in before/after request hooks.

### Challenge 2: Label Cardinality
**Problem:** Using raw paths as labels could create high cardinality.
**Solution:** Implemented `normalize_endpoint()` function to group paths into known categories.

### Challenge 3: Grafana Datasource UID
**Problem:** Dashboard JSON needs correct datasource UID for provisioning.
**Solution:** Set explicit UID in datasource provisioning and reference in dashboard.

### Challenge 4: Docker Internal Networking
**Problem:** Prometheus couldn't reach app on exposed port 8000.
**Solution:** Use internal port 5000 since all services are on same Docker network.

---

## Quick Reference

### URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards |
| Prometheus | http://localhost:9090 | Metric queries |
| App Metrics | http://localhost:8000/metrics | Raw metrics |
| App Health | http://localhost:8000/health | Health check |

### Deployment Commands

```bash
# Deploy stack
cd monitoring
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f prometheus

# Restart after config change
docker compose restart prometheus

# Stop stack
docker compose down

# Stop and remove data
docker compose down -v
```

### Useful PromQL

```promql
# All targets status
up

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# p99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```
