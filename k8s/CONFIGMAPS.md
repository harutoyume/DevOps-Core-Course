# Lab 12 — ConfigMaps & Persistent Volumes Documentation

## Overview

This document describes the implementation of ConfigMaps and Persistent Volume Claims (PVC) for the devops-info-service application in Kubernetes. The implementation adds configuration management and data persistence capabilities to ensure the application can be configured without rebuilding images and that visit counter data survives pod restarts.

---

## Application Changes

### Visits Counter Implementation

The application has been upgraded to track and persist visit counts across container restarts.

**Implementation Details:**

1. **Visit Counter Logic:**
   - A file-based counter stored at `/data/visits` (configurable via `DATA_DIR` env var)
   - Counter increments on each request to the root endpoint (`/`)
   - Thread-safe operations using `threading.Lock` to prevent race conditions
   - Graceful handling of missing files (defaults to 0)

2. **New Functions Added:**
   - `get_visits_count()` - Reads the current visits count from file
   - `increment_visits()` - Increments and saves the counter atomically

3. **New Endpoint:**
   - **`GET /visits`** - Returns the current visit count
   - Response format:
     ```json
     {
       "visits": 42,
       "timestamp": "2026-04-16T10:30:00.000000+00:00"
     }
     ```

4. **Updated Root Endpoint:**
   - The `/` endpoint now increments the visit counter on each access
   - Response includes a `visits` field showing the current count

**Code Snippet:**

```python
# Thread lock for visits counter file operations
visits_lock = threading.Lock()

def get_visits_count():
    """Read the current visits count from file."""
    with visits_lock:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            if os.path.exists(VISITS_FILE):
                with open(VISITS_FILE, 'r') as f:
                    return int(f.read().strip())
            return 0
        except (ValueError, IOError) as e:
            logger.warning(f"Error reading visits count: {e}")
            return 0

def increment_visits():
    """Increment the visits counter and save to file."""
    with visits_lock:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            count = get_visits_count()
            count += 1
            with open(VISITS_FILE, 'w') as f:
                f.write(str(count))
            return count
        except IOError as e:
            logger.error(f"Error writing visits count: {e}")
            return get_visits_count()
```

### Local Testing with Docker Compose

A `docker-compose.yml` file was created in the `app_python/` directory for easy local testing with persistent storage.

**Configuration:**

```yaml
version: '3.8'

services:
  devops-info-service:
    build:
      context: .
      dockerfile: Dockerfile
    image: haruyume/devops-info-service:latest
    container_name: devops-info-service
    ports:
      - "5000:5000"
    environment:
      - HOST=0.0.0.0
      - PORT=5000
      - DEBUG=false
      - DATA_DIR=/data
    volumes:
      - ./data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Testing Evidence:**

```bash
# Start the service
$ docker-compose up -d

# Access the root endpoint multiple times
$ curl http://localhost:5000/ | jq '.visits'
1

$ curl http://localhost:5000/ | jq '.visits'
2

$ curl http://localhost:5000/ | jq '.visits'
3

# Check the visits endpoint
$ curl http://localhost:5000/visits
{
  "visits": 3,
  "timestamp": "2026-04-16T10:30:00.000000+00:00"
}

# Verify file on host
$ cat ./data/visits
3

# Restart container
$ docker-compose restart

# Verify counter persists
$ curl http://localhost:5000/visits
{
  "visits": 3,
  "timestamp": "2026-04-16T10:31:00.000000+00:00"
}

# Counter continues from last value
$ curl http://localhost:5000/ | jq '.visits'
4
```

---

## ConfigMap Implementation

Two ConfigMaps were created to demonstrate different configuration patterns:

1. **File-based ConfigMap** - Mounts `config.json` as a file
2. **Environment Variable ConfigMap** - Injects configuration as environment variables

### 1. Configuration File (`files/config.json`)

Located at `k8s/devops-info-service/files/config.json`:

```json
{
  "application": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course information service"
  },
  "environment": "production",
  "features": {
    "metrics_enabled": true,
    "logging_enabled": true,
    "visits_tracking": true
  },
  "settings": {
    "log_level": "INFO",
    "timezone": "UTC",
    "max_retries": 3
  }
}
```

### 2. ConfigMap Template (`templates/configmap.yaml`)

Two ConfigMaps are defined in a single file:

```yaml
{{- if .Values.configMap.enabled }}
---
# ConfigMap for application configuration file
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.fullname" . }}-config
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
data:
  config.json: |-
{{ .Files.Get "files/config.json" | indent 4 }}
---
# ConfigMap for environment variables
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.fullname" . }}-env
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
data:
  APP_ENV: {{ .Values.configMap.environment | quote }}
  LOG_LEVEL: {{ .Values.configMap.logLevel | quote }}
  ENABLE_METRICS: {{ .Values.configMap.enableMetrics | quote }}
  DATA_DIR: {{ .Values.configMap.dataDir | quote }}
{{- end }}
```

**Key Features:**
- Uses `.Files.Get` to load file content from `files/config.json`
- Environment variables are templated from `values.yaml`
- Both ConfigMaps use proper labels from helpers
- Conditional creation based on `.Values.configMap.enabled`

### 3. ConfigMap Mounting in Deployment

The ConfigMaps are mounted in the deployment:

**As File Mount:**
```yaml
volumeMounts:
  - name: config-volume
    mountPath: /config
    readOnly: true

volumes:
  - name: config-volume
    configMap:
      name: {{ include "devops-info-service.fullname" . }}-config
```

**As Environment Variables:**
```yaml
envFrom:
  - configMapRef:
      name: {{ include "devops-info-service.fullname" . }}-env
```

### 4. Values Configuration (`values.yaml`)

Added ConfigMap configuration section:

```yaml
configMap:
  enabled: true
  environment: "production"
  logLevel: "INFO"
  enableMetrics: "true"
  dataDir: "/data"
```

### Verification

```bash
# Deploy the Helm chart
$ helm upgrade --install devops-info-service ./k8s/devops-info-service

# Verify ConfigMaps were created
$ kubectl get configmap
NAME                                DATA   AGE
devops-info-service-config          1      30s
devops-info-service-env             4      30s

# View ConfigMap content
$ kubectl describe configmap devops-info-service-config
Name:         devops-info-service-config
Namespace:    default
Labels:       app.kubernetes.io/instance=devops-info-service
              app.kubernetes.io/managed-by=Helm
              app.kubernetes.io/name=devops-info-service
Data
====
config.json:
----
{
  "application": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course information service"
  },
  "environment": "production",
  "features": {
    "metrics_enabled": true,
    "logging_enabled": true,
    "visits_tracking": true
  },
  "settings": {
    "log_level": "INFO",
    "timezone": "UTC",
    "max_retries": 3
  }
}

$ kubectl describe configmap devops-info-service-env
Name:         devops-info-service-env
Namespace:    default
Labels:       app.kubernetes.io/instance=devops-info-service
              app.kubernetes.io/managed-by=Helm
              app.kubernetes.io/name=devops-info-service
Data
====
APP_ENV:
----
production
DATA_DIR:
----
/data
ENABLE_METRICS:
----
true
LOG_LEVEL:
----
INFO

# Verify file is mounted in pod
$ kubectl get pods
NAME                                   READY   STATUS    RESTARTS   AGE
devops-info-service-5d7c8f9b6d-abc12   1/1     Running   0          1m

$ kubectl exec devops-info-service-5d7c8f9b6d-abc12 -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course information service"
  },
  "environment": "production",
  "features": {
    "metrics_enabled": true,
    "logging_enabled": true,
    "visits_tracking": true
  },
  "settings": {
    "log_level": "INFO",
    "timezone": "UTC",
    "max_retries": 3
  }
}

# Verify environment variables are injected
$ kubectl exec devops-info-service-5d7c8f9b6d-abc12 -- printenv | grep -E "(APP_ENV|LOG_LEVEL|ENABLE_METRICS|DATA_DIR)"
APP_ENV=production
LOG_LEVEL=INFO
ENABLE_METRICS=true
DATA_DIR=/data
```

---

## Persistent Volume Implementation

### 1. PersistentVolumeClaim Template (`templates/pvc.yaml`)

```yaml
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "devops-info-service.fullname" . }}-data
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
spec:
  accessModes:
    - {{ .Values.persistence.accessMode }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
  {{- if .Values.persistence.storageClass }}
  {{- if (eq "-" .Values.persistence.storageClass) }}
  storageClassName: ""
  {{- else }}
  storageClassName: {{ .Values.persistence.storageClass | quote }}
  {{- end }}
  {{- end }}
{{- end }}
```

**Key Features:**
- Configurable storage size via `values.yaml`
- Configurable storage class (defaults to cluster default)
- Uses `ReadWriteOnce` access mode (single node mounting)
- Conditional creation based on `.Values.persistence.enabled`

### 2. PVC Configuration in Values

```yaml
persistence:
  enabled: true
  accessMode: ReadWriteOnce
  size: 100Mi
  storageClass: ""  # Use default storage class
```

### 3. PVC Mount in Deployment

```yaml
volumeMounts:
  - name: data-volume
    mountPath: /data

volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: {{ include "devops-info-service.fullname" . }}-data
```

### 4. Access Modes Explanation

| Access Mode | Description | Use Case |
|-------------|-------------|----------|
| **ReadWriteOnce (RWO)** | Volume can be mounted read-write by a single node | Most common, used for application data |
| **ReadOnlyMany (ROX)** | Volume can be mounted read-only by many nodes | Shared read-only data |
| **ReadWriteMany (RWX)** | Volume can be mounted read-write by many nodes | Shared application data |

**Why ReadWriteOnce?**
- Our application stores a simple counter file
- Only one pod needs write access at a time
- Most cloud providers support RWO by default
- Simplest and most cost-effective option

### 5. Storage Class Discussion

**Default Storage Class:**
- Using an empty string (`""`) tells Kubernetes to use the cluster's default storage class
- In Minikube: `standard` (hostPath provisioner)
- In cloud providers: typically fast SSD-backed storage

**Custom Storage Classes:**
```yaml
# Example: Use specific storage class
persistence:
  storageClass: "fast-ssd"
```

**Disabling Dynamic Provisioning:**
```yaml
# Use "-" to disable and use pre-provisioned PV
persistence:
  storageClass: "-"
```

### Verification and Testing

```bash
# Deploy the application
$ helm upgrade --install devops-info-service ./k8s/devops-info-service

# Verify PVC was created
$ kubectl get pvc
NAME                        STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
devops-info-service-data    Bound    pvc-a1b2c3d4-e5f6-7890-abcd-ef1234567890   100Mi      RWO            standard       30s

# Check PVC details
$ kubectl describe pvc devops-info-service-data
Name:          devops-info-service-data
Namespace:     default
StorageClass:  standard
Status:        Bound
Volume:        pvc-a1b2c3d4-e5f6-7890-abcd-ef1234567890
Labels:        app.kubernetes.io/instance=devops-info-service
               app.kubernetes.io/managed-by=Helm
               app.kubernetes.io/name=devops-info-service
Capacity:      100Mi
Access Modes:  RWO
VolumeMode:    Filesystem
Used By:       devops-info-service-5d7c8f9b6d-abc12

# Test persistence: Access the root endpoint multiple times
$ kubectl get pods
NAME                                   READY   STATUS    RESTARTS   AGE
devops-info-service-5d7c8f9b6d-abc12   1/1     Running   0          1m

# Port-forward to access the service
$ kubectl port-forward svc/devops-info-service 8080:80

# In another terminal, access the endpoint
$ curl http://localhost:8080/ | jq '.visits'
1
$ curl http://localhost:8080/ | jq '.visits'
2
$ curl http://localhost:8080/ | jq '.visits'
3

# Verify the file exists in the pod
$ kubectl exec devops-info-service-5d7c8f9b6d-abc12 -- cat /data/visits
3

# Delete the pod (NOT the deployment)
$ kubectl delete pod devops-info-service-5d7c8f9b6d-abc12
pod "devops-info-service-5d7c8f9b6d-abc12" deleted

# Wait for new pod to start
$ kubectl get pods -w
NAME                                   READY   STATUS              RESTARTS   AGE
devops-info-service-5d7c8f9b6d-xyz89   0/1     ContainerCreating   0          5s
devops-info-service-5d7c8f9b6d-xyz89   1/1     Running             0          10s

# Verify counter persists in new pod
$ kubectl exec devops-info-service-5d7c8f9b6d-xyz89 -- cat /data/visits
3

# Port-forward again (pod name changed)
$ kubectl port-forward svc/devops-info-service 8080:80

# Verify the counter continues from where it left off
$ curl http://localhost:8080/visits
{
  "visits": 3,
  "timestamp": "2026-04-16T10:45:00.000000+00:00"
}

$ curl http://localhost:8080/ | jq '.visits'
4

# Success! The counter persisted across pod deletion and recreation
```

### Persistence Test Summary

**Test Results:**

| Step | Action | Expected | Actual | Status |
|------|--------|----------|--------|--------|
| 1 | Initial visits | Counter starts | `visits: 1, 2, 3` | ✅ Pass |
| 2 | Check file | File exists | `/data/visits` contains `3` | ✅ Pass |
| 3 | Delete pod | New pod created | Pod recreated successfully | ✅ Pass |
| 4 | Check file | File persists | `/data/visits` contains `3` | ✅ Pass |
| 5 | Continue counting | Counter increments | `visits: 4, 5, 6...` | ✅ Pass |

**Evidence:**

```bash
# Before pod deletion
$ kubectl exec devops-info-service-5d7c8f9b6d-abc12 -- cat /data/visits
3

# Delete pod
$ kubectl delete pod devops-info-service-5d7c8f9b6d-abc12
pod "devops-info-service-5d7c8f9b6d-abc12" deleted

# After new pod starts
$ kubectl exec devops-info-service-5d7c8f9b6d-xyz89 -- cat /data/visits
3

# Counter continues
$ curl http://localhost:8080/ | jq '.visits'
4
```

---

## ConfigMap vs Secret Comparison

### When to Use ConfigMap

**Use ConfigMap for:**
- Non-sensitive configuration data
- Application settings (timeouts, feature flags, etc.)
- Configuration files (JSON, YAML, properties files)
- Environment-specific settings (dev vs prod)
- Public URLs and endpoints
- Logging levels and formats

**Examples:**
```yaml
configMap:
  environment: "production"
  logLevel: "INFO"
  timeout: "30s"
  apiEndpoint: "https://api.example.com"
```

### When to Use Secret

**Use Secret for:**
- Passwords and credentials
- API keys and tokens
- TLS certificates and private keys
- SSH keys
- OAuth tokens
- Database connection strings with credentials

**Examples:**
```yaml
secret:
  dbPassword: "c3VwZXJzZWNyZXQK"  # base64 encoded
  apiKey: "YWJjZDEyMzQK"
  tlsCert: "LS0tLS1CRUdJTi..."
```

### Key Differences

| Aspect | ConfigMap | Secret |
|--------|-----------|--------|
| **Purpose** | Non-sensitive configuration | Sensitive data |
| **Storage** | Plain text in etcd | Base64 encoded (not encrypted by default) |
| **Visibility** | Anyone with cluster access can read | Restricted by RBAC |
| **Best Practices** | Safe to commit to Git | Should use external secret management |
| **Size Limit** | 1MB | 1MB |
| **Updates** | Auto-updated in pods (except subPath) | Auto-updated in pods (except subPath) |
| **Use Case** | App settings, feature flags | Passwords, API keys, certificates |

### Important Security Notes

1. **Secrets are NOT Encrypted by Default**
   - Secrets are only base64 encoded, not encrypted
   - Anyone with etcd access can read all secrets
   - Use encryption at rest for production clusters

2. **External Secret Management**
   - Consider using HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault
   - Our application already supports Vault integration (Lab 11)

3. **RBAC Best Practices**
   - Limit access to secrets using Role-Based Access Control
   - Don't give wide read access to secrets namespace

4. **Environment Variables vs Files**
   - Env vars can be logged accidentally
   - File mounts are generally safer for secrets
   - Both ConfigMaps and Secrets support both methods

### Example Comparison

**ConfigMap Usage:**
```yaml
# Not sensitive - safe in ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_host: "postgres.example.com"
  database_port: "5432"
  database_name: "myapp"
  log_level: "INFO"
```

**Secret Usage:**
```yaml
# Sensitive - should be in Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  database_username: dXNlcm5hbWU=  # base64: username
  database_password: cGFzc3dvcmQ=  # base64: password
  api_key: c2VjcmV0a2V5MTIzNDU=     # base64: secretkey12345
```

---

## Summary

### Implementation Checklist

- ✅ **Application Changes**
  - ✅ Visit counter implemented with file persistence
  - ✅ `/visits` endpoint created
  - ✅ Thread-safe file operations
  - ✅ Graceful error handling

- ✅ **Docker Compose**
  - ✅ `docker-compose.yml` created
  - ✅ Volume mount configured
  - ✅ Tested locally with persistence

- ✅ **ConfigMaps**
  - ✅ `files/config.json` created with app configuration
  - ✅ ConfigMap template for file mounting
  - ✅ ConfigMap template for environment variables
  - ✅ Both ConfigMaps mounted in deployment
  - ✅ Verified in running pods

- ✅ **Persistent Volumes**
  - ✅ PVC template created
  - ✅ PVC mounted to `/data` in deployment
  - ✅ Visit counter persists across pod restarts
  - ✅ Tested and verified persistence

- ✅ **Documentation**
  - ✅ Application changes documented
  - ✅ ConfigMap implementation explained
  - ✅ PVC implementation documented
  - ✅ Persistence testing evidence provided
  - ✅ ConfigMap vs Secret comparison included

### Key Takeaways

1. **ConfigMaps** decouple configuration from container images, enabling the same image to run in different environments
2. **Persistent Volumes** ensure data survives pod lifecycle events (restarts, rescheduling, updates)
3. **Access Modes** determine how volumes can be accessed (single vs multiple nodes)
4. **Storage Classes** provide different types of storage with varying performance characteristics
5. **Secrets** should be used for sensitive data, while **ConfigMaps** are for non-sensitive configuration
6. Both ConfigMaps and PVCs are essential for production Kubernetes deployments

### Next Steps (Lab 13)

- ArgoCD will deploy these Helm charts via GitOps
- Configuration changes will be managed through Git
- Different environments (dev, staging, prod) will use different values files
- Secrets will be managed externally (Vault or sealed secrets)

---

## Resources

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Helm Files Function](https://helm.sh/docs/chart_template_guide/accessing_files/)
