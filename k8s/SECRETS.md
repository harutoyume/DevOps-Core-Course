# Lab 11 — Kubernetes Secrets & HashiCorp Vault

This document provides comprehensive documentation of secret management implementation using both Kubernetes native Secrets and HashiCorp Vault with sidecar injection pattern.

---

## Table of Contents

1. [Kubernetes Secrets](#1-kubernetes-secrets)
2. [Helm Secret Integration](#2-helm-secret-integration)
3. [Resource Management](#3-resource-management)
4. [Vault Integration](#4-vault-integration)
5. [Security Analysis](#5-security-analysis)

---

## 1. Kubernetes Secrets

### 1.1 Creating Secrets with kubectl

**Command to create secret:**
```bash
$ kubectl create secret generic app-credentials --from-literal=username=admin --from-literal=password=secure123
secret/app-credentials created
```

### 1.2 Viewing Secrets

**Command to view secret in YAML format:**
```bash
$ kubectl get secret app-credentials -o yaml
```

**Output:**
```yaml
apiVersion: v1
data:
  password: c2VjdXJlMTIz
  username: YWRtaW4=
kind: Secret
metadata:
  creationTimestamp: "2026-04-09T21:31:18Z"
  name: app-credentials
  namespace: default
  resourceVersion: "4298"
  uid: ab990745-9105-48fd-88d2-4ccb36d8814c
type: Opaque
```

### 1.3 Decoding Base64 Values

**Decoding the username:**
```bash
$ echo "YWRtaW4=" | base64 -d
admin
```

**Decoding the password:**
```bash
$ echo "c2VjdXJlMTIz" | base64 -d
secure123
```

### 1.4 Base64 Encoding vs Encryption

**Critical Understanding: Base64 ≠ Encryption**

- **Base64 encoding** is a reversible encoding scheme that converts binary data to ASCII text
- **NOT encryption** - anyone with access to the Kubernetes API can decode these values
- Secrets are stored in plaintext (base64-encoded) in etcd by default
- Base64 is used for safe transmission, not for security

**Visual Example:**
```
Plain Text → Base64 Encoding → c2VjdXJlMTIz
           ← Base64 Decoding ← c2VjdXJlMTIz
```

This is **NOT** the same as:
```
Plain Text → Encryption (with key) → 8f3a9c2b...
           ← Decryption (needs key) ← 8f3a9c2b...
```

### 1.5 Security Implications

#### Default Security Model

**Kubernetes Secrets are NOT encrypted at rest by default:**

1. **Storage**: Secrets are stored base64-encoded in etcd (Kubernetes data store)
2. **Access**: Anyone with API access can read and decode secrets
3. **Transmission**: Secrets are only encrypted in transit between API server and nodes (TLS)
4. **At Rest**: No encryption by default when stored in etcd

#### Enabling Encryption at Rest

For production environments, you should enable etcd encryption:

**Step 1: Create encryption configuration**
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

**Step 2: Configure API server**
```bash
kube-apiserver --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
```

**Step 3: Encrypt existing secrets**
```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

#### RBAC Requirements

**Principle of Least Privilege:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
  resourceNames: ["app-credentials"]
```

**Best Practices:**
- Grant secret access only to necessary service accounts
- Use namespaces to isolate secrets
- Implement audit logging for secret access
- Rotate secrets regularly

#### Why External Secret Managers?

**Limitations of Kubernetes Secrets:**
- No native secret rotation
- No audit trail by default
- No dynamic secret generation
- Limited access control policies
- Difficult secret lifecycle management

**Benefits of External Secret Managers (Vault, AWS Secrets Manager, etc.):**
- Automatic secret rotation
- Comprehensive audit logging
- Dynamic credential generation
- Fine-grained access policies
- Centralized secret management across multiple clusters
- Encryption at rest by default

---

## 2. Helm Secret Integration

### 2.1 Chart Structure

The Helm chart now includes secret management:

```
k8s/devops-info-service/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-prod.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── serviceaccount.yaml
    ├── secrets.yaml          ← New: Secret template
    ├── _helpers.tpl
    ├── NOTES.txt
    └── hooks/
        ├── pre-install-job.yaml
        └── post-install-job.yaml
```

### 2.2 Secret Template

**File: `templates/secrets.yaml`**

```yaml
{{- if .Values.secrets.enabled -}}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "devops-info-service.fullname" . }}-secret
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
type: Opaque
stringData:
  {{- range $key, $value := .Values.secrets.data }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

**Key Features:**
- Uses `stringData` for plain text values (auto-encoded to base64)
- Conditional rendering based on `secrets.enabled`
- Templated name using Helm helper function
- Standard Kubernetes labels for organization
- Iterates over all secret key-value pairs from values

### 2.3 Values Configuration

**Default configuration in `values.yaml`:**

```yaml
secrets:
  enabled: true
  data:
    DB_USERNAME: "placeholder-user"
    DB_PASSWORD: "placeholder-pass"
    API_KEY: "placeholder-key"
```

**Development configuration in `values-dev.yaml`:**

```yaml
secrets:
  enabled: true
  data:
    DB_USERNAME: "dev-user"
    DB_PASSWORD: "dev-password"
    API_KEY: "dev-api-key-12345"
```

**Important Notes:**
- Never commit real secrets to Git repositories
- Use placeholder values in version control
- Override with `--set` flag or external secret management in production
- Different values per environment for testing isolation

### 2.4 Deployment Secret Injection

**Modified `templates/deployment.yaml` (relevant section):**

```yaml
spec:
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          env:
            {{- toYaml .Values.env | nindent 12 }}
          {{- if .Values.secrets.enabled }}
          envFrom:
            - secretRef:
                name: {{ include "devops-info-service.fullname" . }}-secret
          {{- end }}
```

**Injection Pattern:**
- `envFrom` with `secretRef` injects **all** secret keys as environment variables
- Conditional based on `secrets.enabled` flag
- Secret name dynamically generated from release name
- Alternative: Individual `env` entries with `secretKeyRef` for specific keys

### 2.5 Verification Evidence

**Created secret:**
```bash
$ kubectl get secret -l "app.kubernetes.io/instance=devops-dev"
NAME                                    TYPE     DATA   AGE
devops-dev-devops-info-service-secret   Opaque   3      5m
```

**Environment variables in pod:**
```bash
$ kubectl exec devops-dev-devops-info-service-59bd64575f-6srts -- env | grep -E '(DB_|API_)' | sort
API_KEY=dev-api-key-12345
DB_PASSWORD=dev-password
DB_USERNAME=dev-user
```

**Secrets NOT visible in pod description:**
```bash
$ kubectl describe pod devops-dev-devops-info-service-59bd64575f-6srts | grep -A 20 "Environment:"
    Environment:
      PORT:  5000
      HOST:  0.0.0.0
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-wwswx (ro)
```

**Key Observation:**
- The secret environment variables are **not displayed** in `kubectl describe`
- Values are only accessible inside the container
- This prevents accidental exposure via kubectl commands
- Secret values are still accessible with proper pod exec permissions

---

## 3. Resource Management

### 3.1 Current Resource Configuration

**From `values.yaml`:**

```yaml
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

**Per-environment overrides:**

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-------------|-------------|-----------|----------------|--------------|
| Default     | 100m        | 200m      | 128Mi          | 256Mi        |
| Dev         | 50m         | 100m      | 64Mi           | 128Mi        |
| Prod        | 200m        | 500m      | 256Mi          | 512Mi        |

### 3.2 Requests vs Limits Explained

#### Resource Requests

**Definition:** Guaranteed minimum resources for the container

**Purpose:**
- Used by Kubernetes scheduler to find suitable nodes
- Ensures container gets at least this amount of resources
- Container can use more if available (up to limit)

**Impact:**
- Pod won't be scheduled if no node has sufficient free resources
- QoS class determination (Guaranteed, Burstable, BestEffort)

**Example:**
```yaml
requests:
  cpu: 100m        # Guaranteed 0.1 CPU core
  memory: 128Mi    # Guaranteed 128 MiB memory
```

#### Resource Limits

**Definition:** Maximum resources the container can use

**Purpose:**
- Prevents resource exhaustion
- Protects other pods on the same node
- Enforces resource boundaries

**Behavior:**
- **CPU:** Throttled when limit is reached (container slows down)
- **Memory:** Container is killed (OOMKilled) when limit is exceeded

**Example:**
```yaml
limits:
  cpu: 200m        # Max 0.2 CPU core (throttled beyond this)
  memory: 256Mi    # Max 256 MiB (OOMKilled if exceeded)
```

### 3.3 Quality of Service (QoS) Classes

Based on resource configuration, pods get assigned a QoS class:

| QoS Class | Configuration | Behavior |
|-----------|---------------|----------|
| **Guaranteed** | Requests = Limits for all containers | Highest priority, last to be evicted |
| **Burstable** | Requests < Limits (or only requests set) | Medium priority, evicted before Guaranteed |
| **BestEffort** | No requests or limits set | Lowest priority, first to be evicted |

**Our configuration:** Burstable (requests < limits)

### 3.4 Choosing Appropriate Values

#### Guidelines for Sizing

**CPU:**
```
Request = Average usage during normal operation
Limit = Peak usage during high load (2-3x request)
```

**Memory:**
```
Request = Minimum working memory
Limit = Maximum before OOM (1.5-2x request)
```

#### Measurement Process

1. **Start with estimates:**
   ```yaml
   requests:
     cpu: 100m
     memory: 128Mi
   limits:
     cpu: 500m
     memory: 512Mi
   ```

2. **Monitor actual usage:**
   ```bash
   kubectl top pod devops-dev-devops-info-service-xxxxx
   ```

3. **Adjust based on metrics:**
   - If consistently hitting limits → increase limits
   - If using much less than requests → decrease requests
   - Monitor for OOMKilled events

4. **Load testing:**
   ```bash
   # Use tools like k6, Apache Bench, or hey
   hey -z 30s -c 50 http://service-url/
   ```

#### Production Considerations

**Right-sizing benefits:**
- ✅ Better cluster utilization
- ✅ Faster pod scheduling
- ✅ Cost optimization
- ✅ Improved stability

**Our current configuration rationale:**
- **CPU 100m/200m:** Suitable for I/O-bound Flask application
- **Memory 128Mi/256Mi:** Adequate for Python runtime + application code
- **Dev environment:** Lower resources for cost efficiency
- **Prod environment:** Higher resources for performance and reliability

---

## 4. Vault Integration

### 4.1 Vault Installation

**Add HashiCorp Helm repository:**
```bash
$ helm repo add hashicorp https://helm.releases.hashicorp.com
"hashicorp" has been added to your repositories

$ helm repo update
Hang tight while we grab the latest from your chart repositories...
...Successfully got an update from the "hashicorp" chart repository
Update Complete. ⎈Happy Helming!⎈
```

**Install Vault in dev mode:**
```bash
$ helm install vault hashicorp/vault \
  --set "server.dev.enabled=true" \
  --set "injector.enabled=true"

NAME: vault
LAST DEPLOYED: Fri Apr 10 00:32:46 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
```

**Verify Vault pods:**
```bash
$ kubectl get pods | grep vault
vault-0                                           1/1     Running   0          5m
vault-agent-injector-848dd747d7-2rbcd             1/1     Running   0          5m
```

**Pod Status:**
- `vault-0`: Main Vault server (dev mode)
- `vault-agent-injector`: Mutating webhook for sidecar injection

### 4.2 Vault Configuration

#### Enable KV Secrets Engine

```bash
$ kubectl exec vault-0 -- vault secrets enable -path=secret kv-v2
# Already enabled in dev mode at secret/
```

**Dev mode note:** KV v2 secrets engine is pre-configured at `secret/` path.

#### Create Application Secrets

```bash
$ kubectl exec vault-0 -- vault kv put secret/devops-info-service/config \
  db_host="postgres.default.svc" \
  db_port="5432" \
  api_endpoint="https://api.example.com"

============= Secret Path =============
secret/data/devops-info-service/config

======= Metadata =======
Key                Value
---                -----
created_time       2026-04-09T21:33:53.160180086Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1
```

#### Verify Secrets

```bash
$ kubectl exec vault-0 -- vault kv get secret/devops-info-service/config

============= Secret Path =============
secret/data/devops-info-service/config

======== Data ========
Key             Value
---             -----
api_endpoint    https://api.example.com
db_host         postgres.default.svc
db_port         5432
```

### 4.3 Kubernetes Authentication

#### Enable Kubernetes Auth Method

```bash
$ kubectl exec vault-0 -- vault auth enable kubernetes
Success! Enabled kubernetes auth method at: kubernetes/
```

#### Configure Kubernetes Auth

```bash
$ kubectl exec vault-0 -- sh -c \
  'vault write auth/kubernetes/config \
   kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443"'

Success! Data written to: auth/kubernetes/config
```

**What this does:**
- Tells Vault how to communicate with Kubernetes API
- Uses environment variable available inside pod
- Required for Vault to verify Kubernetes service account tokens

### 4.4 Policy Configuration

#### Create Vault Policy

```bash
$ kubectl exec vault-0 -- sh -c 'vault policy write devops-info-service - <<EOF
path "secret/data/devops-info-service/*" {
  capabilities = ["read"]
}
EOF'

Success! Uploaded policy: devops-info-service
```

**Policy breakdown:**
- **Path:** `secret/data/devops-info-service/*`
  - Note: KV v2 uses `/data/` in the path
  - Wildcard allows access to all secrets under this path
- **Capabilities:** `["read"]`
  - Only read access (principle of least privilege)
  - Cannot create, update, or delete secrets

**Alternative capabilities:**
- `create`: Create new secrets
- `update`: Update existing secrets
- `delete`: Delete secrets
- `list`: List secret names
- `sudo`: Admin operations

### 4.5 Role Configuration

#### Create Kubernetes Role

```bash
$ kubectl exec vault-0 -- vault write auth/kubernetes/role/devops-info-service \
  bound_service_account_names=devops-dev-devops-info-service \
  bound_service_account_namespaces=default \
  policies=devops-info-service \
  ttl=24h
```

**Role verification:**
```bash
$ kubectl exec vault-0 -- vault read auth/kubernetes/role/devops-info-service

Key                                         Value
---                                         -----
bound_service_account_names                 [devops-dev-devops-info-service]
bound_service_account_namespaces            [default]
policies                                    [devops-info-service]
token_ttl                                   24h
ttl                                         24h
```

**Role configuration explained:**
- **bound_service_account_names:** Which K8s service accounts can use this role
- **bound_service_account_namespaces:** Which namespaces are allowed
- **policies:** Vault policies granted to this role
- **ttl:** Token lifetime (renewed automatically by agent)

### 4.6 Vault Agent Injection

#### Deployment Annotations

**Added to `templates/deployment.yaml`:**

```yaml
spec:
  template:
    metadata:
      annotations:
        {{- if .Values.vault.enabled }}
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: {{ .Values.vault.role | quote }}
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/devops-info-service/config"
        {{- end }}
```

**Annotation descriptions:**

| Annotation | Value | Purpose |
|------------|-------|---------|
| `vault.hashicorp.com/agent-inject` | `"true"` | Enable Vault agent sidecar injection |
| `vault.hashicorp.com/role` | `"devops-info-service"` | Vault role to authenticate with |
| `vault.hashicorp.com/agent-inject-secret-config` | `secret/data/...` | Secret path to inject as file |

#### Values Configuration

```yaml
vault:
  enabled: true
  role: "devops-info-service"
```

### 4.7 Sidecar Injection Verification

#### Pod Status with Sidecar

```bash
$ kubectl get pods -l "app.kubernetes.io/instance=devops-dev"
NAME                                              READY   STATUS    RESTARTS   AGE
devops-dev-devops-info-service-5c959bf98d-qmk4v   2/2     Running   0          2m
```

**Key observation:** `2/2` indicates two containers (main + sidecar)

#### Container Names

```bash
$ kubectl get pod devops-dev-devops-info-service-5c959bf98d-qmk4v \
  -o jsonpath='{.spec.containers[*].name}'
devops-info-service vault-agent
```

**Containers:**
1. `devops-info-service`: Main application container
2. `vault-agent`: Vault agent sidecar for secret injection

#### Vault Annotations on Pod

```bash
$ kubectl describe pod devops-dev-devops-info-service-5c959bf98d-qmk4v | grep -A 5 "Annotations:"
Annotations:      vault.hashicorp.com/agent-inject: true
                  vault.hashicorp.com/agent-inject-secret-config: secret/data/devops-info-service/config
                  vault.hashicorp.com/agent-inject-status: injected
                  vault.hashicorp.com/role: devops-info-service
```

**Injection status:** `injected` confirms successful sidecar injection

#### Secrets in Pod Filesystem

```bash
$ kubectl exec devops-dev-devops-info-service-5c959bf98d-qmk4v \
  -c devops-info-service -- ls -la /vault/secrets/
total 8
drwxrwxrwt 2 root    root   60 Apr  9 21:34 .
drwxr-xr-x 3 root    root 4096 Apr  9 21:34 ..
-rw-r--r-- 1 appuser 1000  212 Apr  9 21:34 config
```

**Secret file content:**
```bash
$ kubectl exec devops-dev-devops-info-service-5c959bf98d-qmk4v \
  -c devops-info-service -- cat /vault/secrets/config
data: map[api_endpoint:https://api.example.com db_host:postgres.default.svc db_port:5432]
metadata: map[created_time:2026-04-09T21:33:53.160180086Z custom_metadata:<nil> deletion_time: destroyed:false version:1]
```

**File location:** `/vault/secrets/config`
- Path determined by annotation name suffix (`-secret-config`)
- Contains both secret data and metadata
- Automatically updated when secret changes in Vault

### 4.8 Sidecar Injection Pattern

#### Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                         Pod                              │
│                                                          │
│  ┌────────────────────────┐  ┌─────────────────────────┐│
│  │                        │  │                         ││
│  │   vault-agent          │  │   devops-info-service   ││
│  │   (Sidecar)            │  │   (Main Container)      ││
│  │                        │  │                         ││
│  │  1. Authenticate with  │  │  1. Reads secrets from  ││
│  │     Vault using K8s    │  │     /vault/secrets/     ││
│  │     service account    │  │                         ││
│  │                        │  │  2. Uses secrets in     ││
│  │  2. Fetch secrets from │  │     application logic   ││
│  │     secret path        │  │                         ││
│  │                        │  │  3. No code changes     ││
│  │  3. Write to shared    │  │     needed              ││
│  │     volume at          │  │                         ││
│  │     /vault/secrets/    │  │                         ││
│  │                        │  │                         ││
│  │  4. Renew token &      │  │                         ││
│  │     refresh secrets    │  │                         ││
│  │     automatically      │  │                         ││
│  │                        │  │                         ││
│  └────────┬───────────────┘  └─────────┬───────────────┘│
│           │                            │                 │
│           └────────► Shared Volume ◄───┘                 │
│                   /vault/secrets/                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
                         │
                         │ Authenticates & Fetches Secrets
                         ▼
              ┌──────────────────────┐
              │   HashiCorp Vault    │
              │                      │
              │  - KV Secrets Store  │
              │  - K8s Auth Method   │
              │  - Policies & Roles  │
              └──────────────────────┘
```

#### How Sidecar Injection Works

**Step 1: Mutating Webhook**
- Vault agent injector watches for pod creation
- Detects Vault annotations on pod spec
- Modifies pod specification before creation

**Step 2: Init Container**
- Runs before main container starts
- Authenticates with Vault using service account token
- Fetches initial secrets and writes to shared volume

**Step 3: Sidecar Container**
- Runs alongside main container
- Keeps secrets fresh by renewing tokens
- Updates secret files when they change in Vault
- Handles authentication renewal

**Step 4: Main Container**
- Reads secrets from shared volume at `/vault/secrets/`
- No code changes required
- Application unaware of Vault integration

#### Benefits of Sidecar Pattern

**Advantages:**
- ✅ Zero application code changes
- ✅ Automatic secret renewal
- ✅ Secrets never touch CI/CD pipeline
- ✅ Centralized secret management
- ✅ Audit trail in Vault
- ✅ Works with legacy applications

**Disadvantages:**
- ❌ Additional memory overhead (~50MB per pod)
- ❌ Additional CPU usage
- ❌ Slightly slower pod startup
- ❌ Complexity in debugging

#### Alternative: Vault CSI Driver

For production, consider the Vault CSI (Container Storage Interface) driver:
- More native Kubernetes integration
- Lower resource overhead
- Better performance
- Requires CSI support in cluster

---

## 5. Security Analysis

### 5.1 Kubernetes Secrets vs HashiCorp Vault

#### Comprehensive Comparison

| Feature | Kubernetes Secrets | HashiCorp Vault |
|---------|-------------------|-----------------|
| **Encryption at Rest** | Optional (requires etcd encryption) | Yes, always enabled |
| **Encryption in Transit** | Yes (TLS to nodes) | Yes (TLS everywhere) |
| **Access Control** | RBAC (namespace-level) | Fine-grained policies (path-level) |
| **Audit Logging** | Basic (API audit logs) | Comprehensive (all operations) |
| **Secret Rotation** | Manual only | Automatic (with dynamic secrets) |
| **Dynamic Secrets** | No | Yes (DB, cloud credentials, etc.) |
| **Secret Versioning** | No | Yes (KV v2 engine) |
| **Secret Expiration** | No | Yes (TTL-based) |
| **Multi-cluster** | No (per-cluster) | Yes (centralized) |
| **Complexity** | Low | Medium-High |
| **Setup Time** | Minutes | Hours |
| **Operational Overhead** | Low | Medium |
| **Cost** | Free | Free (OSS) or Paid (Enterprise) |
| **Learning Curve** | Easy | Moderate |
| **Integration Effort** | Minimal | Moderate |
| **Secret Discovery** | Manual documentation | Secret engines & metadata |
| **Compliance** | Basic | Advanced (SOC 2, HIPAA, PCI-DSS) |

#### Detailed Feature Breakdown

**Encryption:**
- **K8s Secrets:** Base64 encoding by default, encryption requires configuration
- **Vault:** AES-256 encryption always, with key rotation capabilities

**Access Control:**
- **K8s Secrets:** RBAC binds to service accounts/users at namespace level
- **Vault:** Path-based policies with granular read/write/list/delete permissions

**Audit:**
- **K8s Secrets:** Kubernetes API audit logs (if enabled)
- **Vault:** Every operation logged with request/response details

**Rotation:**
- **K8s Secrets:** Update secret → restart pods (manual process)
- **Vault:** Dynamic secrets auto-expire, static secrets can auto-rotate

**Dynamic Secrets:**
- **K8s Secrets:** Not supported
- **Vault:** Generate on-demand (DB creds, AWS keys, certificates)

### 5.2 When to Use Each Approach

#### Use Kubernetes Secrets When:

✅ **Development Environments**
- Fast iteration needed
- Secret management complexity not justified
- Learning Kubernetes fundamentals

✅ **Simple Applications**
- Few secrets (< 10)
- Secrets rarely change
- Single cluster deployment

✅ **Non-Critical Data**
- Public API keys (rate-limited, not sensitive)
- Feature flags
- Configuration that's not truly secret

✅ **Resource Constraints**
- Cannot allocate resources for Vault
- No dedicated security team

**Example Use Case:**
```yaml
# Simple microservice with a few API keys
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
data:
  stripe: cHVibGljX2tleQ==
  sendgrid: bm90X3NlY3JldA==
```

#### Use HashiCorp Vault When:

✅ **Production Environments**
- Security is critical
- Compliance requirements (SOC 2, HIPAA, PCI-DSS)
- Need audit trails

✅ **Complex Secret Management**
- Many secrets (> 50)
- Multiple applications sharing secrets
- Multi-cluster deployments
- Multi-cloud infrastructure

✅ **Sensitive Data**
- Database credentials
- API keys with high privileges
- Private keys and certificates
- Customer PII or payment data

✅ **Dynamic Credentials**
- Need short-lived database credentials
- Temporary cloud provider access keys
- Just-in-time certificate generation

✅ **Regulatory Requirements**
- Need comprehensive audit logs
- Must demonstrate encryption at rest
- Require secret rotation policies

**Example Use Case:**
```hcl
# Dynamic database credentials (auto-rotate every 24h)
path "database/creds/readonly" {
  capabilities = ["read"]
}

# Application retrieves fresh credentials automatically
# Old credentials automatically revoked after TTL
```

### 5.3 Hybrid Approach

**Best Practice:** Use both together

```
┌─────────────────────────────────────────┐
│         Application Architecture        │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐  │
│  │    Non-Sensitive Configuration    │  │
│  │    (ConfigMaps & Basic Secrets)   │  │
│  │                                   │  │
│  │  - Feature flags                  │  │
│  │  - Public API keys                │  │
│  │  - Service discovery info         │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │   Sensitive Secrets (Vault)       │  │
│  │                                   │  │
│  │  - Database passwords             │  │
│  │  - Private API keys               │  │
│  │  - TLS certificates               │  │
│  │  - Encryption keys                │  │
│  └───────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### 5.4 Production Recommendations

#### 1. Always Use External Secret Manager in Production

**Never rely on K8s Secrets alone for production:**
```bash
# ❌ Bad for production
kubectl create secret generic db-password --from-literal=password=prod123

# ✅ Good for production
# Secrets stored in Vault, injected via sidecar or CSI driver
```

#### 2. Enable etcd Encryption if Using K8s Secrets

**Configure encryption at rest:**
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <32-byte-base64-key>
```

#### 3. Implement Strict RBAC Policies

**Principle of least privilege:**
```yaml
# Service accounts should only access their own secrets
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["app-specific-secret"]  # Limit to specific secrets
  verbs: ["get"]  # Read-only
```

#### 4. Regular Secret Rotation

**Automated rotation schedule:**
- Database credentials: Every 90 days (or dynamic with Vault)
- API keys: Every 180 days
- TLS certificates: Every 365 days (or Let's Encrypt auto-renewal)
- Encryption keys: Yearly (with proper key migration)

**Vault dynamic secrets (preferred):**
```bash
# Database credentials auto-rotate every 24 hours
vault write database/roles/app \
  db_name=production \
  creation_statements="CREATE USER..." \
  default_ttl="24h" \
  max_ttl="72h"
```

#### 5. Comprehensive Audit Logging

**Enable Kubernetes audit logs:**
```yaml
# /etc/kubernetes/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets"]
```

**Vault audit logging (enabled by default):**
```bash
vault audit enable file file_path=/vault/logs/audit.log
```

#### 6. Never Commit Secrets to Git

**Prevention measures:**
- Use `.gitignore` for secret files
- Pre-commit hooks to detect secrets
- Use tools like `git-secrets`, `truffleHog`, or `gitleaks`
- Secret scanning in CI/CD pipelines

**Example `.gitignore`:**
```gitignore
# Secrets
*.key
*.pem
secrets.yaml
.env
credentials.json
```

#### 7. Separate Secrets by Environment

**Namespace isolation:**
```bash
# Production secrets in prod namespace
kubectl create secret -n production generic db-creds ...

# Development secrets in dev namespace  
kubectl create secret -n development generic db-creds ...
```

**Vault path separation:**
```
secret/prod/database/credentials
secret/staging/database/credentials
secret/dev/database/credentials
```

#### 8. Monitor Secret Access

**Set up alerts for:**
- Unauthorized secret access attempts
- Secret creation/deletion
- Failed Vault authentication
- Token renewal failures
- Policy violations

**Example Prometheus alert:**
```yaml
- alert: UnauthorizedSecretAccess
  expr: kubernetes_audit_event{resource="secrets", verb="get", responseStatus!="200"} > 0
  annotations:
    description: "Unauthorized access to secret {{ $labels.name }}"
```

#### 9. Use Vault Namespaces for Multi-Tenancy

**Vault Enterprise feature:**
```bash
# Create namespace per team
vault namespace create team-a
vault namespace create team-b

# Secrets are isolated
vault kv put -namespace=team-a secret/app key=value
```

#### 10. Implement Secret Scanning

**CI/CD pipeline integration:**
```yaml
# .github/workflows/security.yml
- name: Secret Scanning
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.repository.default_branch }}
    head: HEAD
```

### 5.5 Migration Path

#### Phase 1: Assessment (Week 1-2)
- Inventory all secrets across applications
- Classify secrets by sensitivity
- Identify secret usage patterns
- Document current secret management process

#### Phase 2: Quick Wins (Week 3-4)
- Enable etcd encryption for K8s secrets
- Implement RBAC for secret access
- Set up secret scanning in CI/CD
- Document secret rotation procedures

#### Phase 3: Vault Pilot (Month 2)
- Deploy Vault in non-production
- Migrate one application to Vault
- Train team on Vault basics
- Establish operational procedures

#### Phase 4: Production Migration (Month 3-6)
- Deploy Vault in production with HA
- Migrate critical applications gradually
- Implement monitoring and alerting
- Document disaster recovery procedures

#### Phase 5: Advanced Features (Month 6+)
- Enable dynamic secrets
- Implement auto-rotation
- Set up Vault replication (if Enterprise)
- Integrate with cloud secret managers

---

## Conclusion

This lab demonstrated two approaches to secret management in Kubernetes:

1. **Kubernetes Secrets**: Simple, built-in, suitable for development
2. **HashiCorp Vault**: Enterprise-grade, feature-rich, production-ready

**Key Takeaways:**
- Base64 encoding ≠ Encryption
- Secrets need encryption at rest in production
- External secret managers provide superior security
- Sidecar pattern enables zero-code-change integration
- Always implement least-privilege access control
- Regular rotation and audit logging are critical

**Production Checklist:**
- ✅ Vault or cloud secret manager deployed
- ✅ etcd encryption enabled (if using K8s secrets)
- ✅ RBAC policies implemented
- ✅ Audit logging configured
- ✅ Secret rotation schedule established
- ✅ Monitoring and alerting set up
- ✅ Disaster recovery plan documented
- ✅ Team trained on secret management

