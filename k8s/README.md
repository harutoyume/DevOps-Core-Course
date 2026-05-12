# Kubernetes Deployment Documentation

## Architecture Overview

### Deployment Architecture

This Kubernetes deployment consists of:

- **Deployment**: `devops-info-service` - Manages 5 replicas of the Python Flask application
- **Service**: `devops-info-service` - Exposes the application via NodePort (30080)
- **Pods**: 5 replicas running the containerized application with health monitoring

### Architecture Diagram

```
                                    ┌─────────────────────┐
                                    │   Kubernetes API    │
                                    │   Control Plane     │
                                    └──────────┬──────────┘
                                               │
                                               │
                                    ┌──────────▼──────────┐
                                    │    Deployment       │
                                    │ devops-info-service │
                                    │   (5 replicas)      │
                                    └──────────┬──────────┘
                                               │
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
         ┌──────────▼─────────┐    ┌──────────▼─────────┐    ┌──────────▼─────────┐
         │   Pod 1            │    │   Pod 2            │    │   Pod 3-5          │
         │   Container:5000   │    │   Container:5000   │    │   Container:5000   │
         │   Health: /health  │    │   Health: /health  │    │   Health: /health  │
         │   Resources:       │    │   Resources:       │    │   Resources:       │
         │   128Mi/256Mi      │    │   128Mi/256Mi      │    │   128Mi/256Mi      │
         └────────────────────┘    └────────────────────┘    └────────────────────┘
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │      Service        │
                                    │  NodePort: 30080    │
                                    │  ClusterIP: 80      │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   External Access   │
                                    │  via minikube       │
                                    └─────────────────────┘
```

### Networking Flow

1. External requests → Minikube Service Tunnel → Service (NodePort 30080)
2. Service → Load balances to any of 5 Pods on port 5000
3. Pod → Container responds with Flask application
4. Health checks run every 5-10 seconds on `/health` endpoint

### Resource Allocation Strategy

**Per Pod Resources:**
- **CPU Request**: 100m (0.1 CPU core) - Guaranteed minimum
- **CPU Limit**: 200m (0.2 CPU core) - Maximum allowed
- **Memory Request**: 128Mi - Guaranteed minimum
- **Memory Limit**: 256Mi - Maximum allowed

**Total Resources for 5 Replicas:**
- **CPU Request**: 500m (0.5 CPU cores)
- **CPU Limit**: 1000m (1 CPU core)
- **Memory Request**: 640Mi
- **Memory Limit**: 1280Mi (1.25 GB)

**Rationale:**
- Conservative resource requests ensure pods can be scheduled on minikube
- Limits prevent resource exhaustion and protect cluster stability
- Memory limits prevent OOM kills under normal load
- CPU is throttled rather than killed, providing graceful degradation

---

## Manifest Files

### 1. deployment.yml

**Purpose**: Defines the application deployment with 5 replicas, health checks, and resource management.

**Key Configuration Choices:**

- **Replicas: 5** - Provides high availability and load distribution. Started with 3 as per requirements, scaled to 5 to demonstrate scaling capabilities.
  
- **Image**: `haruyume/devops-info-service:latest` - Uses the Docker image from Lab 2 containing the Python Flask application with health endpoints.

- **Rolling Update Strategy**:
  - `maxSurge: 1` - Allows one extra pod during updates for faster rollouts
  - `maxUnavailable: 0` - Ensures zero downtime by maintaining all replicas during updates

- **Health Probes**:
  - **Liveness Probe**: Checks `/health` every 10s, restarts container after 3 failures
  - **Readiness Probe**: Checks `/health` every 5s, removes from service after 3 failures
  - Both use HTTP GET requests to port 5000

- **Security Context**:
  - `runAsNonRoot: true` - Container runs as non-root user (UID 1000)
  - `allowPrivilegeEscalation: false` - Prevents privilege escalation
  - `readOnlyRootFilesystem: false` - Required for Flask to write temporary files

- **Environment Variables**:
  - `PORT: 5000` - Application listening port
  - `HOST: 0.0.0.0` - Bind to all interfaces

### 2. service.yml

**Purpose**: Exposes the deployment via NodePort for external access in local development.

**Key Configuration Choices:**

- **Type: NodePort** - Chosen for local development with minikube. Exposes service on each node's IP at a static port (30000-32767 range).

- **Port Configuration**:
  - `port: 80` - Service listens on port 80 within cluster
  - `targetPort: 5000` - Routes to container port 5000 (Flask app)
  - `nodePort: 30080` - Fixed external port for consistent access

- **Selector**: `app: devops-info-service` - Matches deployment labels to route traffic to correct pods

**Why NodePort?**
- ClusterIP would only allow internal access (not suitable for local testing)
- LoadBalancer requires cloud provider integration (not available in minikube)
- NodePort provides external access without additional infrastructure

---

## Deployment Evidence

### 1. Initial Cluster Status

```bash
$ kubectl cluster-info
Kubernetes control plane is running at https://127.0.0.1:63961
CoreDNS is running at https://127.0.0.1:63961/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

$ kubectl get nodes
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   8s    v1.35.1
```

### 2. All Resources After Deployment

```bash
$ kubectl get all
NAME                                       READY   STATUS    RESTARTS   AGE
pod/devops-info-service-b99b9d6bc-898gs    1/1     Running   0          62s
pod/devops-info-service-b99b9d6bc-gmstv    1/1     Running   0          24s
pod/devops-info-service-b99b9d6bc-hg4j9    1/1     Running   0          34s
pod/devops-info-service-b99b9d6bc-t7b88    1/1     Running   0          44s
pod/devops-info-service-b99b9d6bc-xh6ff    1/1     Running   0          53s

NAME                          TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/devops-info-service   NodePort    10.105.146.153   <none>        80:30080/TCP   3m13s
service/kubernetes            ClusterIP   10.96.0.1        <none>        443/TCP        3m23s

NAME                                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-info-service   5/5     5            5           3m14s

NAME                                             DESIRED   CURRENT   READY   AGE
replicaset.apps/devops-info-service-86c8574846   0         0         0       119s
replicaset.apps/devops-info-service-b99b9d6bc    5         5         5       3m13s
```

### 3. Detailed Pod and Service View

```bash
$ kubectl get pods,svc -o wide
NAME                                      READY   STATUS    RESTARTS   AGE   IP           NODE       NOMINATED NODE   READINESS GATES
pod/devops-info-service-b99b9d6bc-5pk8c   1/1     Running   0          51s   10.244.0.4   minikube   <none>           <none>
pod/devops-info-service-b99b9d6bc-r47d4   1/1     Running   0          51s   10.244.0.5   minikube   <none>           <none>
pod/devops-info-service-b99b9d6bc-snw87   1/1     Running   0          51s   10.244.0.6   minikube   <none>           <none>

NAME                          TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE   SELECTOR
service/devops-info-service   NodePort    10.105.146.153   <none>        80:30080/TCP   51s   app=devops-info-service
service/kubernetes            ClusterIP   10.96.0.1        <none>        443/TCP        61s   <none>
```

### 4. Deployment Details

```bash
$ kubectl describe deployment devops-info-service
Name:                   devops-info-service
Namespace:              default
CreationTimestamp:      Thu, 26 Mar 2026 21:40:47 +0300
Labels:                 app=devops-info-service
                        environment=development
                        version=1.0.1
Annotations:            deployment.kubernetes.io/revision: 3
Selector:               app=devops-info-service
Replicas:               5 desired | 5 updated | 5 total | 5 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  0 max unavailable, 1 max surge
Pod Template:
  Labels:  app=devops-info-service
           version=1.0.1
  Containers:
   devops-info-service:
    Image:      haruyume/devops-info-service:latest
    Port:       5000/TCP
    Host Port:  0/TCP
    Limits:
      cpu:     200m
      memory:  256Mi
    Requests:
      cpu:      100m
      memory:   128Mi
    Liveness:   http-get http://:5000/health delay=10s timeout=5s period=10s #success=1 #failure=3
    Readiness:  http-get http://:5000/health delay=5s timeout=3s period=5s #success=1 #failure=3
    Environment:
      PORT:        5000
      HOST:        0.0.0.0
    Mounts:        <none>
  Volumes:         <none>
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
```

### 5. Service Details

```bash
$ kubectl describe service devops-info-service
Name:                     devops-info-service
Namespace:                default
Labels:                   app=devops-info-service
Annotations:              <none>
Selector:                 app=devops-info-service
Type:                     NodePort
IP Family Policy:         SingleStack
IP Families:              IPv4
IP:                       10.105.146.153
IPs:                      10.105.146.153
Port:                     http  80/TCP
TargetPort:               5000/TCP
NodePort:                 http  30080/TCP
Endpoints:                10.244.0.14:5000,10.244.0.15:5000,10.244.0.16:5000 + 2 more...
Session Affinity:         None
External Traffic Policy:  Cluster
Internal Traffic Policy:  Cluster
```

### 6. Application Working - Health Check

```bash
$ curl -s http://127.0.0.1:51244/health
{"status":"healthy","timestamp":"2026-03-26T18:44:02.235069+00:00","uptime_seconds":41}
```

### 7. Application Working - Main Endpoint

```bash
$ curl -s http://127.0.0.1:51244/ | python3 -m json.tool
{
  "endpoints": [
    {"description": "Service information", "method": "GET", "path": "/"},
    {"description": "Health check", "method": "GET", "path": "/health"},
    {"description": "Prometheus metrics", "method": "GET", "path": "/metrics"}
  ],
  "request": {
    "client_ip": "10.244.0.1",
    "method": "GET",
    "path": "/",
    "user_agent": "curl/8.7.1"
  },
  "runtime": {
    "current_time": "2026-03-26T18:41:33.710743+00:00",
    "timezone": "UTC",
    "uptime_human": "32 seconds",
    "uptime_seconds": 32
  },
  "service": {
    "description": "DevOps course info service",
    "framework": "Flask",
    "name": "devops-info-service",
    "version": "1.0.0"
  },
  "system": {
    "architecture": "aarch64",
    "cpu_count": 8,
    "hostname": "devops-info-service-b99b9d6bc-5pk8c",
    "platform": "Linux",
    "platform_version": "#1 SMP Thu Mar 20 16:32:56 UTC 2025",
    "python_version": "3.13.12"
  }
}
```

---

## Operations Performed

### 1. Deploy Application

```bash
# Apply manifests
$ kubectl apply -f k8s/deployment.yml
deployment.apps/devops-info-service created

$ kubectl apply -f k8s/service.yml
service/devops-info-service created

# Monitor rollout
$ kubectl rollout status deployment/devops-info-service
Waiting for deployment "devops-info-service" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "devops-info-service" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "devops-info-service" rollout to finish: 2 of 3 updated replicas are available...
deployment "devops-info-service" successfully rolled out
```

### 2. Scaling Demonstration

```bash
# Scale from 3 to 5 replicas
$ kubectl scale deployment devops-info-service --replicas=5
deployment.apps/devops-info-service scaled

# Monitor scaling
$ kubectl rollout status deployment/devops-info-service
Waiting for deployment "devops-info-service" rollout to finish: 3 of 5 updated replicas are available...
Waiting for deployment "devops-info-service" rollout to finish: 4 of 5 updated replicas are available...
deployment "devops-info-service" successfully rolled out

# Verify all replicas running
$ kubectl get pods -l app=devops-info-service
NAME                                  READY   STATUS    RESTARTS   AGE
devops-info-service-b99b9d6bc-5pk8c   1/1     Running   0          63s
devops-info-service-b99b9d6bc-bkt2w   1/1     Running   0          12s
devops-info-service-b99b9d6bc-r47d4   1/1     Running   0          63s
devops-info-service-b99b9d6bc-snw87   1/1     Running   0          63s
devops-info-service-b99b9d6bc-whjcc   1/1     Running   0          12s
```

**Scaling worked flawlessly:**
- New pods created within seconds
- All pods passed health checks before marked ready
- No downtime during scaling operation
- Load automatically distributed across all 5 replicas

### 3. Rolling Update Demonstration

```bash
# Update deployment manifest (changed version label from 1.0.0 to 1.0.1)
$ kubectl apply -f k8s/deployment.yml
deployment.apps/devops-info-service configured

# Watch rolling update
$ kubectl rollout status deployment/devops-info-service
Waiting for deployment "devops-info-service" rollout to finish: 1 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 2 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 3 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 4 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 1 old replicas are pending termination...
deployment "devops-info-service" successfully rolled out

# View rollout history
$ kubectl rollout history deployment/devops-info-service
deployment.apps/devops-info-service 
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

# Verify new pods with updated label
$ kubectl get pods -l app=devops-info-service --show-labels
NAME                                   READY   STATUS    RESTARTS   AGE   LABELS
devops-info-service-86c8574846-4kdtj   1/1     Running   0          35s   app=devops-info-service,pod-template-hash=86c8574846,version=1.0.1
devops-info-service-86c8574846-56sj8   1/1     Running   0          15s   app=devops-info-service,pod-template-hash=86c8574846,version=1.0.1
devops-info-service-86c8574846-8s7z4   1/1     Running   0          53s   app=devops-info-service,pod-template-hash=86c8574846,version=1.0.1
devops-info-service-86c8574846-8s9qv   1/1     Running   0          44s   app=devops-info-service,pod-template-hash=86c8574846,version=1.0.1
devops-info-service-86c8574846-lg2vn   1/1     Running   0          24s   app=devops-info-service,pod-template-hash=86c8574846,version=1.0.1
```

**Zero Downtime Verified:**
- Rolling update strategy (`maxUnavailable: 0`) ensured continuous availability
- Old pods remained running until new pods passed readiness probes
- Service continued routing traffic throughout the update
- Update took ~48 seconds with smooth pod transitions

### 4. Rollback Demonstration

```bash
# Rollback to previous revision
$ kubectl rollout undo deployment/devops-info-service
deployment.apps/devops-info-service rolled back

# Monitor rollback
$ kubectl rollout status deployment/devops-info-service
Waiting for deployment "devops-info-service" rollout to finish: 1 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 2 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 3 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 4 out of 5 new replicas have been updated...
Waiting for deployment "devops-info-service" rollout to finish: 1 old replicas are pending termination...
deployment "devops-info-service" successfully rolled back

# Verify rollback
$ kubectl rollout history deployment/devops-info-service
deployment.apps/devops-info-service 
REVISION  CHANGE-CAUSE
2         <none>
3         <none>

$ kubectl get pods -l app=devops-info-service
NAME                                   READY   STATUS    RESTARTS   AGE
devops-info-service-b99b9d6bc-898gs    1/1     Running   0          62s
devops-info-service-b99b9d6bc-gmstv    1/1     Running   0          24s
devops-info-service-b99b9d6bc-hg4j9    1/1     Running   0          34s
devops-info-service-b99b9d6bc-t7b88    1/1     Running   0          44s
devops-info-service-b99b9d6bc-xh6ff    1/1     Running   0          53s
```

**Rollback Success:**
- Pods reverted to previous version (1.0.0)
- Same rolling update strategy applied during rollback
- Zero downtime maintained
- Application continued serving requests throughout process

### 5. Service Access

```bash
# Get service URL via minikube
$ minikube service devops-info-service --url
http://127.0.0.1:51244

# Test health endpoint
$ curl http://127.0.0.1:51244/health
{"status":"healthy","timestamp":"2026-03-26T18:44:02.235069+00:00","uptime_seconds":41}

# Test main endpoint
$ curl http://127.0.0.1:51244/
{...full JSON response with service info...}
```

**Alternative Access Methods:**

Using `kubectl port-forward`:
```bash
$ kubectl port-forward service/devops-info-service 8080:80
$ curl http://localhost:8080/health
```

Direct access via NodePort (if minikube IP is accessible):
```bash
$ minikube ip
192.168.49.2
$ curl http://192.168.49.2:30080/health
```

---

## Production Considerations

### Health Checks Implementation

**Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Why These Values?**
- `initialDelaySeconds: 10` - Gives container time to start (Flask initialization)
- `periodSeconds: 10` - Checks every 10 seconds (balanced between responsiveness and overhead)
- `timeoutSeconds: 5` - Allows slow responses without false positives
- `failureThreshold: 3` - Requires 3 consecutive failures before restart (30 seconds grace period)

**Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

**Why Different from Liveness?**
- Faster `initialDelaySeconds` (5s) - Can start receiving traffic sooner
- More frequent checks (`periodSeconds: 5`) - Quick removal from load balancer if unhealthy
- Shorter timeout (3s) - Don't route traffic to slow pods
- Uses same `/health` endpoint for consistency

**Health Endpoint Implementation:**
The Flask application provides a `/health` endpoint that returns:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-26T18:44:02.235069+00:00",
  "uptime_seconds": 41
}
```

This simple endpoint:
- Returns 200 OK status
- Executes quickly (no heavy operations)
- Indicates application is running and responsive
- Could be enhanced to check database connections, external dependencies, etc.

### Resource Limits Rationale

**Memory:**
- **Request: 128Mi** - Flask application typically uses 50-80Mi at idle
- **Limit: 256Mi** - Allows for request spikes and memory growth
- Prevents OOM kills under normal load
- If limit exceeded, pod is killed and restarted (liveness probe)

**CPU:**
- **Request: 100m** - Minimal baseline for HTTP requests
- **Limit: 200m** - Handles request bursts without impacting other pods
- CPU is throttled, not killed (graceful degradation)
- Suitable for I/O-bound Flask application

**Testing Recommendations:**
- Run load tests to validate resource allocation
- Monitor actual usage with `kubectl top pods`
- Adjust based on production metrics (use HPA for auto-scaling)

### Production Improvements

#### 1. High Availability
- [ ] Deploy across multiple nodes with node affinity rules
- [ ] Use pod anti-affinity to spread replicas across nodes
- [ ] Implement PodDisruptionBudget (min 60% available)
- [ ] Add topology spread constraints

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: kubernetes.io/hostname
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: devops-info-service
```

#### 2. Configuration Management
- [ ] Move environment variables to ConfigMap
- [ ] Use Secrets for sensitive data (API keys, passwords)
- [ ] Implement external configuration (consul, etcd)
- [ ] Version ConfigMaps for rollback capability

#### 3. Resource Management
- [ ] Implement Horizontal Pod Autoscaler (HPA)
  - Scale based on CPU/memory metrics
  - Scale based on custom metrics (request rate, queue depth)
- [ ] Use Vertical Pod Autoscaler (VPA) for right-sizing
- [ ] Set resource quotas per namespace
- [ ] Implement Limit Ranges for defaults

#### 4. Networking & Security
- [ ] Replace NodePort with Ingress + TLS
- [ ] Implement Network Policies for pod-to-pod communication
- [ ] Add authentication/authorization (OAuth, mTLS)
- [ ] Use service mesh (Istio, Linkerd) for advanced traffic management
- [ ] Implement rate limiting and WAF rules

#### 5. Monitoring & Observability
- [ ] Deploy Prometheus for metrics collection
- [ ] Set up Grafana dashboards for visualization
- [ ] Implement structured logging with fluentd/fluent-bit
- [ ] Add distributed tracing (Jaeger, Zipkin)
- [ ] Configure alerting (PagerDuty, Slack)
- [ ] Monitor golden signals (latency, traffic, errors, saturation)

#### 6. Deployment Strategy
- [ ] Implement GitOps with ArgoCD or Flux
- [ ] Use Helm charts for templating and versioning
- [ ] Add progressive delivery (canary, blue-green)
- [ ] Implement automated rollback on metrics degradation
- [ ] Use admission controllers for policy enforcement

#### 7. Backup & Disaster Recovery
- [ ] Backup etcd regularly
- [ ] Document disaster recovery procedures
- [ ] Test cluster restoration process
- [ ] Implement multi-region/multi-cluster setup
- [ ] Use Velero for cluster backups

#### 8. Security Hardening
- [ ] Implement Pod Security Standards (restricted)
- [ ] Use read-only root filesystem where possible
- [ ] Drop all capabilities, add only required ones
- [ ] Enable security scanning (Trivy, Falco)
- [ ] Regular security audits and penetration testing
- [ ] Use private container registry with image scanning

---

## Challenges & Solutions

### Challenge 1: Minikube Cluster Not Running

**Issue**: Initial `kubectl cluster-info` failed with connection refused error.

```
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

**Root Cause**: Minikube cluster was not started or was in stopped state.

**Solution**:
```bash
$ minikube start
* minikube v1.38.1 on Darwin 26.2 (arm64)
* Using the docker driver based on existing profile
* Starting "minikube" primary control-plane node in "minikube" cluster
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

**Debugging Steps Used**:
1. Checked if kubectl was installed: `which kubectl`
2. Checked minikube status: `minikube status`
3. Started minikube cluster: `minikube start`
4. Verified cluster: `kubectl cluster-info`

**Learning**: Always verify cluster is running before applying manifests. Use `minikube status` to check state.

---

### Challenge 2: Container Image Pull Delay

**Issue**: Pods stayed in `ContainerCreating` state for several seconds.

**Root Cause**: Docker image needed to be pulled from Docker Hub to minikube cluster's local cache.

**Solution**: 
- Waited for initial image pull to complete
- Used `kubectl rollout status` to monitor progress
- Future deployments faster due to cached image

**Debugging Steps Used**:
```bash
$ kubectl get pods
NAME                                  READY   STATUS              RESTARTS   AGE
devops-info-service-b99b9d6bc-5pk8c   0/1     ContainerCreating   0          9s

$ kubectl describe pod devops-info-service-b99b9d6bc-5pk8c
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  10s   default-scheduler  Successfully assigned pod
  Normal  Pulling    10s   kubelet            Pulling image "haruyume/devops-info-service:latest"
  Normal  Pulled     2s    kubelet            Successfully pulled image
```

**Optimization for Production**:
- Use ImagePullPolicy: IfNotPresent (avoid always pulling)
- Pre-pull images on nodes during deployment
- Use local registry or registry cache
- Implement image verification and vulnerability scanning

---

### Challenge 3: Understanding Rolling Update Behavior

**Issue**: Initially unclear how maxSurge and maxUnavailable interact during updates.

**Configuration**:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

**What This Means**:
- **maxUnavailable: 0** - All 5 pods must stay available (no pod removed from service until replacement ready)
- **maxSurge: 1** - Can create 1 extra pod (total 6 pods during update)

**Update Flow Observed**:
1. Create new pod #1 (6 pods total: 5 old + 1 new)
2. Wait for new pod #1 to pass readiness probe
3. Terminate old pod #1 (back to 5 pods: 4 old + 1 new)
4. Repeat for remaining 4 pods

**Why This Ensures Zero Downtime**:
- Old pod continues serving traffic until new pod is ready
- Service never routes to unready pods
- Load balancer always has 5 healthy endpoints

**Alternative Strategies Considered**:
- `maxSurge: 2, maxUnavailable: 0` - Faster updates (2 pods at once) but uses more resources
- `maxSurge: 0, maxUnavailable: 1` - No extra resources but allows brief capacity reduction
- `maxSurge: 1, maxUnavailable: 1` - Fastest but risks service degradation

**Learning**: Zero downtime requires either maxUnavailable: 0 OR enough replicas that losing one doesn't impact service. Our configuration prioritizes availability over update speed.

---

### Challenge 4: Service Access Methods Confusion

**Issue**: Multiple ways to access NodePort service - which to use?

**Methods Available**:

1. **Minikube Service Tunnel** (Used in this lab):
```bash
$ minikube service devops-info-service --url
http://127.0.0.1:51244
```
- Creates tunnel from localhost to minikube
- Dynamic port on localhost
- Requires terminal to stay open
- Best for interactive testing

2. **kubectl Port-Forward**:
```bash
$ kubectl port-forward service/devops-info-service 8080:80
$ curl http://localhost:8080
```
- Forwards local port to service
- Works with any cluster type
- Requires terminal to stay open
- Good for debugging specific pods

3. **Direct NodePort Access**:
```bash
$ minikube ip
192.168.49.2
$ curl http://192.168.49.2:30080/health
```
- Direct access via node IP and NodePort
- Works when node IP is routable
- Consistent port (30080)
- Best for automation/scripts

**Learning**: Each method has use cases. Minikube service tunnel is most user-friendly for local development. Production would use Ingress or LoadBalancer.

---

### Challenge 5: Debugging Pod Health Issues

**Tools and Commands Learned**:

1. **Check Pod Status**:
```bash
$ kubectl get pods
$ kubectl get pods -o wide  # Shows node and IP
$ kubectl get pods --watch  # Real-time updates
```

2. **Describe Pod for Events**:
```bash
$ kubectl describe pod <pod-name>
```
Shows:
- Image pull status
- Container start failures
- Health probe failures
- Resource constraints
- Scheduling issues

3. **View Logs**:
```bash
$ kubectl logs <pod-name>
$ kubectl logs <pod-name> --previous  # Previous container instance
$ kubectl logs <pod-name> --follow    # Tail logs
```

4. **Check Endpoints**:
```bash
$ kubectl get endpoints devops-info-service
NAME                  ENDPOINTS                                                      AGE
devops-info-service   10.244.0.14:5000,10.244.0.15:5000,10.244.0.16:5000 + 2 more   5m
```
Verifies service is routing to healthy pods.

5. **Test from Inside Cluster**:
```bash
$ kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
/ $ curl http://devops-info-service/health
```

**Learning**: Kubernetes provides rich debugging tools. Start with `get pods`, use `describe` for events, check `logs` for application issues, verify `endpoints` for service routing.

---

### What I Learned About Kubernetes

#### 1. Declarative vs Imperative
- **Declarative** (manifests): Define desired state, Kubernetes makes it happen
- **Imperative** (commands): Tell Kubernetes exactly what to do
- Production uses declarative (GitOps, version control)
- Imperative useful for quick testing/debugging

#### 2. Controllers and Reconciliation
- Kubernetes constantly reconciles actual state with desired state
- Deployment controller manages ReplicaSets
- ReplicaSet controller manages Pods
- Controllers are resilient - recover from failures automatically

#### 3. Labels and Selectors Are Critical
- Labels tie everything together
- Service finds Pods via selector
- Deployment manages Pods via matchLabels
- Essential for organization and filtering

#### 4. Resource Management Is Not Optional
- Without requests/limits, pods can starve resources
- Requests guarantee minimum resources (used for scheduling)
- Limits prevent resource exhaustion
- Production clusters enforce these with LimitRanges

#### 5. Health Checks Prevent Cascade Failures
- Liveness: Restart unhealthy containers
- Readiness: Remove unhealthy pods from load balancer
- Both are needed for zero-downtime deployments
- Simple health endpoint is crucial

#### 6. Rolling Updates Are Powerful
- Zero downtime with proper configuration
- Gradual rollout reduces risk
- Easy rollback if issues detected
- Strategy configuration impacts speed vs. safety tradeoff

#### 7. Kubernetes Is Complex But Logical
- Many moving parts (Pods, Services, Deployments, ReplicaSets)
- Each component has specific responsibility
- Abstractions build on each other
- Understanding the layers is key to troubleshooting

#### 8. Local Development vs Production
- Minikube great for learning but limited
- NodePort works locally, Ingress for production
- Single-node cluster doesn't test HA scenarios
- Resource constraints different from real clusters

---

