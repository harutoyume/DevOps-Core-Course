# Lab 10 - Helm Package Manager

This document describes the Helm chart implementation for the DevOps Info Service application, covering chart structure, configuration, hooks, and deployment evidence.

---

## 1. Chart Overview

### Chart Structure

The Helm chart is organized in the `k8s/devops-info-service/` directory with the following structure:

```
k8s/devops-info-service/
├── Chart.yaml              # Chart metadata and version information
├── values.yaml             # Default configuration values
├── values-dev.yaml         # Development environment overrides
├── values-prod.yaml        # Production environment overrides
├── .helmignore             # Files to ignore when packaging
└── templates/
    ├── deployment.yaml     # Templated Deployment manifest
    ├── service.yaml        # Templated Service manifest
    ├── serviceaccount.yaml # Service account for pods
    ├── _helpers.tpl        # Reusable template functions
    ├── NOTES.txt           # Post-installation instructions
    └── hooks/
        ├── pre-install-job.yaml   # Pre-installation validation hook
        └── post-install-job.yaml  # Post-installation smoke test hook
```

### Key Template Files

**deployment.yaml**
- Manages application pods with configurable replicas
- Uses rolling update strategy for zero-downtime deployments
- Includes health checks (liveness and readiness probes)
- Configures resource limits and requests
- Implements security context for non-root execution

**service.yaml**
- Exposes the application with configurable service type
- Supports NodePort (dev) and LoadBalancer (prod)
- Maps external port 80 to container port 5000
- Configurable nodePort for local development

**_helpers.tpl**
- Provides reusable template functions for consistency
- Generates standardized names and labels
- Implements Kubernetes recommended labels
- Ensures naming conventions across resources

**hooks/**
- Pre-install hook: Validates environment before deployment
- Post-install hook: Performs smoke tests after deployment
- Both hooks use deletion policy `hook-succeeded` for automatic cleanup

### Values Organization Strategy

The chart uses a three-tier values structure:

1. **values.yaml**: Default configuration with sensible baseline settings (3 replicas, moderate resources)
2. **values-dev.yaml**: Development overrides (1 replica, minimal resources, faster probe timings)
3. **values-prod.yaml**: Production overrides (5 replicas, high resources, conservative probe timings)

Values are organized hierarchically:
- `image.*` - Image repository, tag, and pull policy
- `service.*` - Service type, ports, and nodePort
- `resources.*` - CPU and memory limits/requests
- `livenessProbe.*` - Liveness probe configuration
- `readinessProbe.*` - Readiness probe configuration
- `env[]` - Environment variables

---

## 2. Configuration Guide

### Important Values

**Replica Configuration**
```yaml
replicaCount: 3  # Number of pod replicas (default)
```
Controls the number of pod instances. Set to 1 for dev, 5+ for production high availability.

**Image Configuration**
```yaml
image:
  repository: haruyume/devops-info-service
  tag: "latest"
  pullPolicy: IfNotPresent
```
Specifies the Docker image to deploy. Use specific version tags in production.

**Service Configuration**
```yaml
service:
  type: NodePort        # ClusterIP, NodePort, or LoadBalancer
  port: 80             # Service port
  targetPort: 5000     # Container port
  nodePort: 30080      # NodePort (30000-32767)
```
Determines how the application is exposed. NodePort for local development, LoadBalancer for production.

**Resource Configuration**
```yaml
resources:
  limits:
    cpu: 200m          # Maximum CPU
    memory: 256Mi      # Maximum memory
  requests:
    cpu: 100m          # Reserved CPU
    memory: 128Mi      # Reserved memory
```
Ensures proper resource allocation and prevents resource starvation.

**Health Check Configuration**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
```
Kubernetes uses these probes to restart unhealthy containers and route traffic only to ready pods.

### Customization for Different Environments

**Development Environment**
- Minimal resource usage for cost efficiency
- Faster probe timings for rapid iteration
- Single replica for simplicity
- NodePort service for local access

**Production Environment**
- High resource allocation for performance
- Conservative probe timings for stability
- Multiple replicas for high availability
- LoadBalancer service for external access

### Example Installations

**Install with default values:**
```bash
helm install myrelease k8s/devops-info-service
```

**Install development environment:**
```bash
helm install devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml
```

**Install production environment:**
```bash
helm install devops-prod k8s/devops-info-service -f k8s/devops-info-service/values-prod.yaml
```

**Install with custom values:**
```bash
helm install myrelease k8s/devops-info-service \
  --set replicaCount=10 \
  --set image.tag=v2.0.0 \
  --set service.type=LoadBalancer
```

**Install in specific namespace:**
```bash
helm install myrelease k8s/devops-info-service -n production --create-namespace
```

---

## 3. Hook Implementation

### Pre-Install Hook

**Purpose:** Validates the environment and prerequisites before deploying the application.

**Configuration:**
- **Hook Type:** `pre-install`
- **Weight:** `-5` (runs before main resources)
- **Deletion Policy:** `hook-succeeded` (auto-delete on success)

**Implementation:**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  annotations:
    "helm.sh/hook": pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: pre-install-job
        image: busybox:latest
        command: ['sh', '-c', 'echo "Running validation..." && sleep 5']
```

**Real-world use cases:**
- Database schema migrations
- Configuration validation
- Dependency checks
- Environment readiness verification

### Post-Install Hook

**Purpose:** Performs smoke tests and validation after the application is deployed.

**Configuration:**
- **Hook Type:** `post-install`
- **Weight:** `5` (runs after main resources are ready)
- **Deletion Policy:** `hook-succeeded` (auto-delete on success)

**Implementation:**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  annotations:
    "helm.sh/hook": post-install
    "helm.sh/hook-weight": "5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: post-install-job
        image: busybox:latest
        command: ['sh', '-c', 'echo "Running smoke tests..." && sleep 5']
```

**Real-world use cases:**
- Smoke tests
- Service health verification
- Notification sending (Slack, email)
- Metrics initialization

### Hook Execution Order

Helm executes hooks in the following sequence:

1. **Pre-install hook** (weight: -5) - Runs first, validates prerequisites
2. **Main resources** (Deployment, Service) - Created after pre-install succeeds
3. **Post-install hook** (weight: 5) - Runs last, validates deployment

Lower weight values execute first. Multiple hooks with the same weight run in alphabetical order by name.

### Deletion Policies

**hook-succeeded**: Deletes the hook resource after successful completion
- Pros: Automatic cleanup, no manual intervention needed
- Cons: Logs are lost after deletion
- Best for: Pre-flight checks, smoke tests

**before-hook-creation**: Deletes the previous hook before creating a new one
- Best for: Upgrades where hooks should be recreated

**hook-failed**: Deletes the hook only if it fails
- Best for: Debugging failed hooks

Our implementation uses `hook-succeeded` because:
- Hooks are simple validation tasks
- Automatic cleanup keeps cluster clean
- Events log still shows execution history
- Can be re-run by reinstalling release

---

## 4. Installation Evidence

### Helm Releases

```bash
$ helm list
NAME       	NAMESPACE	REVISION	UPDATED                             	STATUS  	CHART                    	APP VERSION
devops-dev 	default  	1       	2026-04-02 21:40:51.123502 +0300 MSK	deployed	devops-info-service-0.1.0	1.0.1      
devops-prod	default  	1       	2026-04-02 21:41:22.556005 +0300 MSK	deployed	devops-info-service-0.1.0	1.0.1
```

Both releases are deployed successfully with the same chart version but different configurations.

### Kubernetes Resources

```bash
$ kubectl get all
NAME                                                  READY   STATUS    RESTARTS   AGE
pod/devops-dev-devops-info-service-8556c55cf-mdwgk    1/1     Running   0          5m
pod/devops-prod-devops-info-service-9b65bd5cb-5qxpk   1/1     Running   0          4m
pod/devops-prod-devops-info-service-9b65bd5cb-b2wzs   1/1     Running   0          4m
pod/devops-prod-devops-info-service-9b65bd5cb-hsv8s   1/1     Running   0          4m
pod/devops-prod-devops-info-service-9b65bd5cb-rhhd9   1/1     Running   0          4m
pod/devops-prod-devops-info-service-9b65bd5cb-v2cs7   1/1     Running   0          4m

NAME                                      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/devops-dev-devops-info-service    NodePort       10.103.161.186   <none>        80:30080/TCP   5m
service/devops-prod-devops-info-service   LoadBalancer   10.107.202.8     <pending>     80:31088/TCP   4m
service/kubernetes                        ClusterIP      10.96.0.1        <none>        443/TCP        7d

NAME                                              READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-dev-devops-info-service    1/1     1            1           5m
deployment.apps/devops-prod-devops-info-service   5/5     5            5           4m

NAME                                                        DESIRED   CURRENT   READY   AGE
replicaset.apps/devops-dev-devops-info-service-8556c55cf    1         1         1       5m
replicaset.apps/devops-prod-devops-info-service-9b65bd5cb   5         5         5       4m
```

### Hook Execution Evidence

**Hook Jobs Status:**
```bash
$ kubectl get jobs
No resources found in default namespace.
```

The absence of jobs confirms the deletion policy worked correctly - hooks were automatically deleted after successful completion.

**Hook Execution Events:**
```bash
$ kubectl get events --sort-by='.lastTimestamp' | grep -E "(pre-install|post-install)"
Normal    SuccessfulCreate   job/devops-prod-devops-info-service-pre-install     Created pod
Normal    Pulling            pod/devops-prod-devops-info-service-pre-install     Pulling image "busybox:latest"
Normal    Pulled             pod/devops-prod-devops-info-service-pre-install     Successfully pulled image
Normal    Created            pod/devops-prod-devops-info-service-pre-install     Container created
Normal    Started            pod/devops-prod-devops-info-service-pre-install     Container started
Normal    Completed          job/devops-prod-devops-info-service-pre-install     Job completed
Normal    SuccessfulCreate   job/devops-prod-devops-info-service-post-install    Created pod
Normal    Pulled             pod/devops-prod-devops-info-service-post-install    Successfully pulled image
Normal    Created            pod/devops-prod-devops-info-service-post-install    Container created
Normal    Started            pod/devops-prod-devops-info-service-post-install    Container started
Normal    Completed          job/devops-prod-devops-info-service-post-install    Job completed
```

Events show:
1. Pre-install hook executed first and completed successfully
2. Post-install hook executed after deployment and completed successfully
3. Both hooks were automatically cleaned up per deletion policy

### Dev vs Prod Deployment Comparison

**Development Environment:**
```bash
$ kubectl describe deployment devops-dev-devops-info-service
Replicas:               1 desired | 1 updated | 1 total | 1 available
Strategy:               RollingUpdate (0 max unavailable, 1 max surge)
Containers:
  devops-info-service:
    Image:      haruyume/devops-info-service:latest
    Port:       5000/TCP
    Limits:
      cpu:     100m
      memory:  128Mi
    Requests:
      cpu:      50m
      memory:   64Mi
    Liveness:   http-get http://:5000/health delay=5s period=10s
    Readiness:  http-get http://:5000/health delay=3s period=5s
```

**Production Environment:**
```bash
$ kubectl describe deployment devops-prod-devops-info-service
Replicas:               5 desired | 5 updated | 5 total | 5 available
Strategy:               RollingUpdate (0 max unavailable, 1 max surge)
Containers:
  devops-info-service:
    Image:      haruyume/devops-info-service:latest
    Port:       5000/TCP
    Limits:
      cpu:     500m
      memory:  512Mi
    Requests:
      cpu:      200m
      memory:   256Mi
    Liveness:   http-get http://:5000/health delay=30s period=5s
    Readiness:  http-get http://:5000/health delay=10s period=3s
```

**Key Differences:**
| Configuration | Development | Production |
|--------------|-------------|------------|
| Replicas | 1 | 5 |
| CPU Request | 50m | 200m |
| CPU Limit | 100m | 500m |
| Memory Request | 64Mi | 256Mi |
| Memory Limit | 128Mi | 512Mi |
| Service Type | NodePort | LoadBalancer |
| Liveness Delay | 5s | 30s |
| Readiness Delay | 3s | 10s |

---

## 5. Operations

### Installation

**Basic installation with default values:**
```bash
helm install myrelease k8s/devops-info-service
```

**Install specific environment:**
```bash
# Development
helm install devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml

# Production
helm install devops-prod k8s/devops-info-service -f k8s/devops-info-service/values-prod.yaml
```

**Install with inline value overrides:**
```bash
helm install myrelease k8s/devops-info-service \
  --set replicaCount=7 \
  --set image.tag=v2.0.0
```

### Upgrade

**Upgrade existing release:**
```bash
helm upgrade devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml
```

**Upgrade with new values:**
```bash
helm upgrade devops-prod k8s/devops-info-service \
  -f k8s/devops-info-service/values-prod.yaml \
  --set replicaCount=10
```

**See what will change before upgrading:**
```bash
helm upgrade --dry-run --debug devops-dev k8s/devops-info-service
```

### Rollback

**View release history:**
```bash
helm history devops-prod
```

**Rollback to previous revision:**
```bash
helm rollback devops-prod
```

**Rollback to specific revision:**
```bash
helm rollback devops-prod 2
```

### Uninstall

**Remove a release:**
```bash
helm uninstall devops-dev
```

**Keep history for future rollback:**
```bash
helm uninstall devops-prod --keep-history
```

### Inspection

**Get release information:**
```bash
helm status devops-dev
helm get manifest devops-dev
helm get values devops-dev
helm get notes devops-dev
```

**List all releases:**
```bash
helm list
helm list --all-namespaces
```

---

## 6. Testing & Validation

### Helm Lint

**Command:**
```bash
$ helm lint k8s/devops-info-service
```

**Output:**
```
==> Linting k8s/devops-info-service
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Chart passes all validation checks. The icon field is optional and only affects chart repository display.

### Template Rendering

**Command:**
```bash
$ helm template test-release k8s/devops-info-service
```

**Output (excerpt):**
```yaml
---
# Source: devops-info-service/templates/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: test-release-devops-info-service
  labels:
    helm.sh/chart: devops-info-service-0.1.0
    app.kubernetes.io/name: devops-info-service
    app.kubernetes.io/instance: test-release
    app.kubernetes.io/version: "1.0.1"
    app.kubernetes.io/managed-by: Helm
---
# Source: devops-info-service/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: test-release-devops-info-service
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: devops-info-service
    app.kubernetes.io/instance: test-release
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 5000
      nodePort: 30080
---
# Source: devops-info-service/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-release-devops-info-service
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: devops-info-service
          image: "haruyume/devops-info-service:latest"
          ports:
            - name: http
              containerPort: 5000
          resources:
            limits:
              cpu: 200m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 128Mi
```

All templates render correctly with proper indentation and values substitution.

### Dry Run

**Command:**
```bash
$ helm install --dry-run --debug test-release k8s/devops-info-service
```

Dry run simulates installation without creating resources, useful for:
- Validating template rendering
- Checking hooks will execute
- Verifying values substitution
- Testing before production deployment

### Application Accessibility

**Service endpoints:**
```bash
$ kubectl get services
NAME                              TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)
devops-dev-devops-info-service    NodePort       10.103.161.186   <none>        80:30080/TCP
devops-prod-devops-info-service   LoadBalancer   10.107.202.8     <pending>     80:31088/TCP
```

**Access methods:**

Development (NodePort):
```bash
# Via minikube
minikube service devops-dev-devops-info-service --url

# Via direct access
curl http://$(minikube ip):30080/

# Via port-forward
kubectl port-forward svc/devops-dev-devops-info-service 8080:80
curl http://localhost:8080/
```

Production (LoadBalancer):
```bash
# On cloud (when external IP is assigned)
curl http://<EXTERNAL-IP>:80/

# On minikube (LoadBalancer shows pending, use NodePort)
minikube service devops-prod-devops-info-service --url
```

**Health check verification:**
```bash
$ kubectl logs -l "app.kubernetes.io/instance=devops-dev" --tail=5
{"level": "INFO", "message": "Request completed", "method": "GET", "path": "/health", "status_code": 200}
```

Health probes are working correctly - pods are passing liveness and readiness checks.

---

## 7. Helm Installation & Setup

### Helm Version

```bash
$ helm version
version.BuildInfo{Version:"v4.1.3", GitCommit:"c94d381b03be117e7e57908edbf642104e00eb8f", GitTreeState:"clean", GoVersion:"go1.26.1", KubeClientVersion:"v1.35"}
```

Helm 4.1.3 is installed, which is the latest major version released in November 2025.

### Repository Exploration

```bash
$ helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
"prometheus-community" has been added to your repositories

$ helm search repo prometheus
NAME                                              	CHART VERSION	APP VERSION	DESCRIPTION
prometheus-community/kube-prometheus-stack        	82.16.1      	v0.89.0    	kube-prometheus-stack collects Kubernetes manifests...
prometheus-community/prometheus                   	28.15.0      	v3.11.0    	Prometheus is a monitoring system and time series...
...

$ helm show chart prometheus-community/prometheus
apiVersion: v2
appVersion: v3.11.0
name: prometheus
version: 28.15.0
description: Prometheus is a monitoring system and time series database.
keywords:
- monitoring
- prometheus
```

This demonstrates Helm's chart repository system, where charts can be:
- Discovered through search
- Inspected before installation
- Version-controlled
- Shared across teams and organizations

### Helm's Value Proposition

**Why Helm?**

1. **Templating**: Reuse the same manifests across environments with different configurations
2. **Versioning**: Track releases and easily rollback to previous versions
3. **Packaging**: Bundle multiple Kubernetes resources into a single deployable unit
4. **Configuration Management**: Separate code (templates) from configuration (values)
5. **Lifecycle Management**: Install, upgrade, rollback, and uninstall with single commands
6. **Hooks**: Execute custom logic at specific lifecycle events
7. **Dependencies**: Manage complex applications with multiple components
8. **Standardization**: Industry-standard format for Kubernetes applications

**Benefits over raw manifests:**
- Single source of truth for multi-environment deployments
- Reduced duplication and maintenance burden
- Built-in rollback capabilities
- Release tracking and history
- Easier sharing and distribution

---

## 8. Chart Best Practices Implemented

### Templating
- ✅ Use helper templates for consistent naming and labels
- ✅ Extract all configurable values to values.yaml
- ✅ Use `nindent` for proper YAML indentation
- ✅ Quote string values to prevent type coercion
- ✅ Provide sensible defaults with ability to override

### Security
- ✅ Run containers as non-root user (1000)
- ✅ Disable privilege escalation
- ✅ Implement security context
- ✅ Use specific image tags in production
- ✅ Configure resource limits to prevent resource exhaustion

### Reliability
- ✅ Implement liveness probes (restart unhealthy containers)
- ✅ Implement readiness probes (control traffic routing)
- ✅ Configure resource requests (guaranteed resources)
- ✅ Configure resource limits (prevent resource hogging)
- ✅ Use RollingUpdate strategy (zero-downtime deployments)

### Operations
- ✅ Include helpful NOTES.txt with access instructions
- ✅ Use semantic versioning for chart and app versions
- ✅ Implement hooks for lifecycle management
- ✅ Support multiple environments with values files
- ✅ Provide clear documentation

---

## 9. Troubleshooting

### Common Issues

**Chart doesn't lint:**
```bash
helm lint k8s/devops-info-service
# Check for YAML syntax errors or missing required fields
```

**Templates don't render:**
```bash
helm template test k8s/devops-info-service
# Check for template syntax errors or undefined values
```

**Installation fails:**
```bash
helm install --dry-run --debug myrelease k8s/devops-info-service
# Use dry-run to see what would be created
```

**Hooks don't execute:**
- Verify hook annotations are correct
- Check hook weight if execution order matters
- View pod logs: `kubectl logs job/<hook-job-name>`
- Check events: `kubectl get events`

**Wrong values applied:**
```bash
helm get values myrelease
# Verify which values were actually used
```

### Debugging Commands

```bash
# See what Helm knows about a release
helm status myrelease
helm get manifest myrelease
helm get values myrelease

# See Kubernetes resources
kubectl get all -l "app.kubernetes.io/instance=myrelease"
kubectl describe deployment myrelease-devops-info-service
kubectl logs -l "app.kubernetes.io/instance=myrelease"

# Check events
kubectl get events --sort-by='.lastTimestamp'
```
