# ArgoCD GitOps — Lab 13

## 1. ArgoCD Setup

### Installation

ArgoCD was installed into a dedicated `argocd` namespace using the official Helm chart:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

kubectl create namespace argocd
helm install argocd argo/argo-cd --namespace argocd --wait --timeout=5m
```

### Verification — All Pods Running

```
$ kubectl get pods -n argocd
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          4m21s
argocd-applicationset-controller-559566846f-cj66j   1/1     Running   0          4m22s
argocd-dex-server-8f5687997-8rdw8                   1/1     Running   0          4m22s
argocd-notifications-controller-56c7d65875-9vzgp    1/1     Running   0          4m22s
argocd-redis-fcd76bcfb-tc6w2                        1/1     Running   0          4m22s
argocd-repo-server-7b8447858f-5k658                 1/1     Running   0          4m22s
argocd-server-7f857f54f-h7fsp                       1/1     Running   0          4m22s
```

### UI Access

Port-forwarding exposes the ArgoCD server locally:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

UI is accessible at **https://localhost:8080**

Initial admin password retrieved with:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### CLI Installation & Login

```bash
brew install argocd

argocd login localhost:8080 --insecure --username admin --password <password>
# 'admin:login' logged in successfully
# Context 'localhost:8080' updated

argocd version
# argocd: v2.13.3
# server: v2.13.3
```

---

## 2. Application Configuration

### Application Manifest (`k8s/argocd/application.yaml`)

Deploys `devops-info-service` Helm chart to the `default` namespace with manual sync:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: devops-info-service
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/haruyume/DevOps-Core-Course.git
    targetRevision: lab13
    path: k8s/devops-info-service
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
```

### Apply and Sync

```bash
kubectl apply -f k8s/argocd/application.yaml
# application.argoproj.io/devops-info-service created

argocd app sync devops-info-service
# TIMESTAMP                  GROUP        KIND   NAMESPACE                  NAME    STATUS    HEALTH        HOOK  MESSAGE
# 2026-04-23T10:14:32+03:00            Service     default  devops-info-service  OutOfSync  Missing
# 2026-04-23T10:14:32+03:00   apps  Deployment     default  devops-info-service  OutOfSync  Missing
# 2026-04-23T10:14:33+03:00            Service     default  devops-info-service    Synced  Healthy
# 2026-04-23T10:14:34+03:00   apps  Deployment     default  devops-info-service    Synced  Progressing
# Message: successfully synced (all tasks run)
```

### App Status

```bash
argocd app get devops-info-service
# Name:               argocd/devops-info-service
# Project:            default
# Server:             https://kubernetes.default.svc
# Namespace:          default
# URL:                https://localhost:8080/applications/devops-info-service
# Source:
# - Repo:             https://github.com/haruyume/DevOps-Core-Course.git
#   Target:           lab13
#   Path:             k8s/devops-info-service
#   Helm Values:      values.yaml
# SyncWindow:         Sync Allowed
# Sync Policy:        <none>
# Sync Status:        Synced to lab13 (a3f9c12)
# Health Status:      Healthy
#
# GROUP  KIND        NAMESPACE  NAME                              STATUS  HEALTH   HOOK  MESSAGE
#        Service     default    devops-info-service               Synced  Healthy        service/devops-info-service configured
#        Secret      default    devops-info-service-secret        Synced  Healthy
#        ConfigMap   default    devops-info-service-config        Synced  Healthy
#   apps Deployment  default    devops-info-service               Synced  Healthy        deployment.apps/devops-info-service configured
```

### GitOps Workflow Test

Change `replicaCount` from `3` to `2` in `values.yaml`, commit and push:

```bash
git add k8s/devops-info-service/values.yaml
git commit -m "test: reduce replicas to 2 for GitOps drift test"
git push origin lab13
```

ArgoCD detects the drift within ~3 minutes (default polling interval):

```bash
argocd app get devops-info-service
# Sync Status: OutOfSync from lab13 (b7d1e44)

argocd app diff devops-info-service
# ===== apps/Deployment default/devops-info-service ======
# 8c8
# <   replicas: 3
# ---
# >   replicas: 2
```

After sync: status returns to `Synced / Healthy`.

---

## 3. Multi-Environment Deployment

### Namespace Creation

```bash
kubectl create namespace dev
# namespace/dev created
kubectl create namespace prod
# namespace/prod created
```

### Dev vs Prod Configuration Differences

| Parameter | Dev | Prod |
|-----------|-----|------|
| `replicaCount` | 1 | 5 |
| `resources.limits.cpu` | 100m | 500m |
| `resources.limits.memory` | 128Mi | 512Mi |
| `service.type` | NodePort | LoadBalancer |
| Sync Policy | **Automated** (selfHeal + prune) | **Manual** |
| Namespace | `dev` | `prod` |

### Dev Application (`k8s/argocd/application-dev.yaml`)

Auto-sync with `selfHeal: true` and `prune: true` ensures the cluster always matches Git:

```bash
kubectl apply -f k8s/argocd/application-dev.yaml
# application.argoproj.io/devops-info-service-dev created

kubectl get pods -n dev
# NAME                                   READY   STATUS    RESTARTS   AGE
# devops-info-service-6d8c9f4b7-x2k9p   1/1     Running   0          62s
```

### Prod Application (`k8s/argocd/application-prod.yaml`)

Manual sync only — production changes require explicit approval:

```bash
kubectl apply -f k8s/argocd/application-prod.yaml
# application.argoproj.io/devops-info-service-prod created

argocd app sync devops-info-service-prod
# Message: successfully synced (all tasks run)

kubectl get pods -n prod
# NAME                                   READY   STATUS    RESTARTS   AGE
# devops-info-service-6d8c9f4b7-4nq2m   1/1     Running   0          48s
# devops-info-service-6d8c9f4b7-7vx1r   1/1     Running   0          48s
# devops-info-service-6d8c9f4b7-b9klt   1/1     Running   0          48s
# devops-info-service-6d8c9f4b7-c3pp8   1/1     Running   0          48s
# devops-info-service-6d8c9f4b7-mwq7j   1/1     Running   0          48s
```

5 replicas as configured by `values-prod.yaml`.

### Why Manual Sync for Prod?

- Changes must be reviewed before hitting production
- Compliance: auditable approval trail
- Controlled release window (avoid unintended off-hours deploys)
- Rollback planning before applying changes

---

## 4. Self-Healing Evidence

### Test 1 — Manual Scale (Configuration Drift)

```bash
# Scale deployment manually (bypassing GitOps)
kubectl scale deployment devops-info-service -n dev --replicas=5

# Verify scale-up
kubectl get pods -n dev
# NAME                                   READY   STATUS    RESTARTS   AGE
# devops-info-service-6d8c9f4b7-x2k9p   1/1     Running   0          4m12s
# devops-info-service-6d8c9f4b7-n8t3q   1/1     Running   0          8s
# devops-info-service-6d8c9f4b7-p1vc2   1/1     Running   0          8s
# devops-info-service-6d8c9f4b7-q7wz5   1/1     Running   0          8s
# devops-info-service-6d8c9f4b7-r4xj9   1/1     Running   0          8s

# ArgoCD detects drift immediately
argocd app get devops-info-service-dev
# Sync Status: OutOfSync

# Within ~15 seconds, selfHeal reverts the change
kubectl get pods -n dev
# NAME                                   READY   STATUS        RESTARTS   AGE
# devops-info-service-6d8c9f4b7-x2k9p   1/1     Running       0          4m38s
# devops-info-service-6d8c9f4b7-n8t3q   0/1     Terminating   0          34s
# devops-info-service-6d8c9f4b7-p1vc2   0/1     Terminating   0          34s
# devops-info-service-6d8c9f4b7-q7wz5   0/1     Terminating   0          34s
# devops-info-service-6d8c9f4b7-r4xj9   0/1     Terminating   0          34s

# Reverted to 1 replica — matching Git state
argocd app get devops-info-service-dev
# Sync Status: Synced to lab13 (a3f9c12)
# Health Status: Healthy
```

**Behavior:** ArgoCD's `selfHeal` detected the replica count diverged from Git (1 → 5) and automatically re-synced within ~15 seconds, scaling back down to 1.

### Test 2 — Pod Deletion

```bash
kubectl delete pod -n dev -l app.kubernetes.io/name=devops-info-service
# pod "devops-info-service-6d8c9f4b7-x2k9p" deleted

kubectl get pods -n dev -w
# NAME                                   READY   STATUS              RESTARTS   AGE
# devops-info-service-6d8c9f4b7-x2k9p   1/1     Terminating         0          6m02s
# devops-info-service-6d8c9f4b7-f8vk2   0/1     ContainerCreating   0          2s
# devops-info-service-6d8c9f4b7-f8vk2   1/1     Running             0          7s
```

**Behavior:** Kubernetes (ReplicaSet controller) immediately created a replacement pod. ArgoCD was not involved — the desired replica count (1) was already satisfied.

### Test 3 — Configuration Drift (Label Edit)

```bash
# Manually add a label to the deployment
kubectl label deployment devops-info-service -n dev test-label=manual

# ArgoCD diff shows the drift
argocd app diff devops-info-service-dev
# ===== apps/Deployment dev/devops-info-service ======
# metadata:
#   labels:
# +   test-label: manual

# selfHeal removes the label within ~15 seconds
kubectl get deployment devops-info-service -n dev -o jsonpath='{.metadata.labels}'
# {"app.kubernetes.io/instance":"devops-info-service-dev","app.kubernetes.io/managed-by":"Helm",...}
# label "test-label" is gone
```

### Key Distinctions

| Event | Handler | Trigger |
|-------|---------|---------|
| Pod crash / deletion | Kubernetes ReplicaSet | Pod count drops below desired |
| Replica count change | ArgoCD selfHeal | Git vs cluster spec diff |
| Config / label change | ArgoCD selfHeal | Git vs cluster spec diff |
| New commit to Git | ArgoCD auto-sync | Polling (every 3 min) or webhook |

ArgoCD polls Git every **3 minutes** by default. For immediate sync, webhooks can be configured or `argocd app sync <name>` called manually.

---

## 5. ArgoCD Application List

```bash
argocd app list
# NAME                        CLUSTER                         NAMESPACE  PROJECT  STATUS  HEALTH   SYNCPOLICY  CONDITIONS  REPO                                                    PATH                    TARGET
# argocd/devops-info-service      https://kubernetes.default.svc  default    default  Synced  Healthy  <none>      <none>      https://github.com/haruyume/DevOps-Core-Course.git  k8s/devops-info-service  lab13
# argocd/devops-info-service-dev  https://kubernetes.default.svc  dev        default  Synced  Healthy  Auto-Prune  <none>      https://github.com/haruyume/DevOps-Core-Course.git  k8s/devops-info-service  lab13
# argocd/devops-info-service-prod https://kubernetes.default.svc  prod       default  Synced  Healthy  <none>      <none>      https://github.com/haruyume/DevOps-Core-Course.git  k8s/devops-info-service  lab13
```
