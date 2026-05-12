# Argo Rollouts - Progressive Delivery

This document describes the implementation and testing of Argo Rollouts for progressive delivery strategies including Canary and Blue-Green deployments.

## Table of Contents

1. [Argo Rollouts Setup](#argo-rollouts-setup)
2. [Canary Deployment](#canary-deployment)
3. [Blue-Green Deployment](#blue-green-deployment)
4. [Strategy Comparison](#strategy-comparison)
5. [CLI Commands Reference](#cli-commands-reference)

---

## Argo Rollouts Setup

### Installation Verification

**1. Controller Installation**

```bash
# Create namespace
kubectl create namespace argo-rollouts

# Install Argo Rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Verify controller is running
kubectl get pods -n argo-rollouts
```

**Output:**
```
NAME                            READY   STATUS    RESTARTS   AGE
argo-rollouts-5f64f8d68-w9zlp   1/1     Running   0          5m
```

**2. kubectl Plugin Installation**

```bash
# macOS
brew install argoproj/tap/kubectl-argo-rollouts

# Verify installation
kubectl argo rollouts version
```

**Output:**
```
kubectl-argo-rollouts: v1.8.3+49fa151
  BuildDate: 2025-06-04T22:19:21Z
  GitCommit: 49fa1516cf71672b69e265267da4e1d16e1fe114
  GitTreeState: clean
  GoVersion: go1.23.9
  Compiler: gc
  Platform: darwin/amd64
```

**3. Dashboard Installation**

```bash
# Install dashboard
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/dashboard-install.yaml

# Access dashboard via port-forward
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

Access at: http://localhost:3100

### Rollout vs Deployment

**Key Differences:**

| Feature | Deployment | Rollout |
|---------|-----------|---------|
| Progressive Delivery | No | Yes (Canary, Blue-Green) |
| Traffic Management | Basic rolling update | Advanced traffic shifting |
| Manual Promotion | No | Yes |
| Automated Rollback | Limited | Advanced with metrics analysis |
| Strategy Options | RollingUpdate, Recreate | Canary, Blue-Green |

---

## Canary Deployment

### Configuration

**Rollout Strategy:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: devops-info-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devops-info-service
  template:
    # Pod template spec...
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: {}  # Manual promotion required
        - setWeight: 40
        - pause: { duration: 30s }
        - setWeight: 60
        - pause: { duration: 30s }
        - setWeight: 80
        - pause: { duration: 30s }
        - setWeight: 100
```

**Canary Steps Explained:**

1. **Step 0-1**: Deploy canary pods with 20% weight, wait for manual promotion
2. **Step 2-3**: Increase to 40% weight, auto-pause for 30 seconds
3. **Step 4-5**: Increase to 60% weight, auto-pause for 30 seconds
4. **Step 6-7**: Increase to 80% weight, auto-pause for 30 seconds
5. **Step 8**: Full rollout to 100%

### Canary Rollout Progression

**Initial State:**

```bash
$ kubectl argo rollouts get rollout devops-info-devops-info-service
```

**Output at 20% Canary (Paused for Manual Promotion):**
```
Name:            devops-info-devops-info-service
Namespace:       default
Status:          ॥ Paused
Message:         CanaryPauseStep
Strategy:        Canary
  Step:          1/9
  SetWeight:     20
  ActualWeight:  25
Images:          haruyume/devops-info-service:latest (stable)
                 haruyume/devops-info-service:v2 (canary)
Replicas:
  Desired:       3
  Current:       4
  Updated:       1
  Ready:         4
  Available:     4

NAME                                                         KIND        STATUS     AGE   INFO
⟳ devops-info-devops-info-service                            Rollout     ॥ Paused   100s  
├──# revision:2                                                                           
│  └──⧉ devops-info-devops-info-service-544f6fdfb7           ReplicaSet  ✔ Healthy  38s   canary
│     └──□ devops-info-devops-info-service-544f6fdfb7-lcm74  Pod         ✔ Running  38s   ready:1/1
└──# revision:1                                                                           
   └──⧉ devops-info-devops-info-service-58cf784744           ReplicaSet  ✔ Healthy  100s  stable
      ├──□ devops-info-devops-info-service-58cf784744-7swqs  Pod         ✔ Running  100s  ready:1/1
      ├──□ devops-info-devops-info-service-58cf784744-cmpnr  Pod         ✔ Running  100s  ready:1/1
      └──□ devops-info-devops-info-service-58cf784744-qpkgd  Pod         ✔ Running  100s  ready:1/1
```

**Key Observations:**
- 1 canary pod (revision 2) with v2 image
- 3 stable pods (revision 1) with latest image
- Actual weight is 25% (1 out of 4 pods)
- Rollout is paused, waiting for manual promotion

### Manual Promotion

```bash
# Promote to next step
$ kubectl argo rollouts promote devops-info-devops-info-service
rollout 'devops-info-devops-info-service' promoted
```

After promotion, the rollout automatically progresses through steps 2-8 with the configured pause durations.

### Canary Rollback

**Aborting a Rollout:**

```bash
# Abort during canary progression
$ kubectl argo rollouts abort devops-info-devops-info-service
rollout 'devops-info-devops-info-service' aborted
```

**Output After Abort:**
```
Name:            devops-info-devops-info-service
Namespace:       default
Status:          ✖ Degraded
Message:         RolloutAborted: Rollout aborted update to revision 2
Strategy:        Canary
  Step:          0/9
  SetWeight:     0
  ActualWeight:  0
Images:          haruyume/devops-info-service:latest (stable)
Replicas:
  Desired:       3
  Current:       3
  Updated:       0
  Ready:         3
  Available:     3

NAME                                                         KIND        STATUS         AGE    INFO
⟳ devops-info-devops-info-service                            Rollout     ✖ Degraded     2m23s  
├──# revision:2                                                                                
│  └──⧉ devops-info-devops-info-service-544f6fdfb7           ReplicaSet  • ScaledDown   81s    canary
│     └──□ devops-info-devops-info-service-544f6fdfb7-lcm74  Pod         ◌ Terminating  81s    ready:1/1
└──# revision:1                                                                                
   └──⧉ devops-info-devops-info-service-58cf784744           ReplicaSet  ✔ Healthy      2m23s  stable
      ├──□ devops-info-devops-info-service-58cf784744-7swqs  Pod         ✔ Running      2m23s  ready:1/1
      ├──□ devops-info-devops-info-service-58cf784744-cmpnr  Pod         ✔ Running      2m23s  ready:1/1
      └──□ devops-info-devops-info-service-58cf784744-6nbc5  Pod         ✔ Running      23s    ready:1/1
```

**Key Observations:**
- Canary pods are terminated
- Traffic is shifted back to stable version
- Rollout shows "Degraded" status with abort message
- All pods are restored to stable version (revision 1)

---

## Blue-Green Deployment

### Configuration

**Rollout Strategy:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: devops-info-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devops-info-service
  template:
    # Pod template spec...
  strategy:
    blueGreen:
      activeService: devops-info-service
      previewService: devops-info-service-preview
      autoPromotionEnabled: false  # Manual promotion
      # autoPromotionSeconds: 30  # Or auto-promote after 30s
```

### Services Configuration

**Active Service** (`devops-info-service`):
- Serves production traffic
- Always points to stable/active version
- Updated only after promotion

**Preview Service** (`devops-info-service-preview`):
- Serves new version for testing
- Points to green (new) version
- Allows testing before promotion

```bash
# Check services
$ kubectl get svc | grep devops-info
devops-info-bg-devops-info-service           NodePort    10.109.167.86    <none>        80:30080/TCP
devops-info-bg-devops-info-service-preview   NodePort    10.106.147.201   <none>        80:30081/TCP
```

### Blue-Green Rollout Flow

**1. Initial State (Blue Active):**

```bash
$ kubectl argo rollouts get rollout devops-info-bg-devops-info-service
```

**Output:**
```
Name:            devops-info-bg-devops-info-service
Namespace:       default
Status:          ✔ Healthy
Strategy:        BlueGreen
Images:          haruyume/devops-info-service:latest (stable, active)
Replicas:
  Desired:       3
  Current:       3
  Updated:       3
  Ready:         3
  Available:     3

NAME                                                            KIND        STATUS     AGE  INFO
⟳ devops-info-bg-devops-info-service                            Rollout     ✔ Healthy  38s  
└──# revision:1                                                                             
   └──⧉ devops-info-bg-devops-info-service-7486f9b7d4           ReplicaSet  ✔ Healthy  38s  stable,active
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-w6rzj  Pod         ✔ Running  38s  ready:1/1
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-x6b8z  Pod         ✔ Running  38s  ready:1/1
      └──□ devops-info-bg-devops-info-service-7486f9b7d4-zpppg  Pod         ✔ Running  38s  ready:1/1
```

**2. After Update (Green Preview, Blue Active):**

```bash
# Update to v2
$ kubectl argo rollouts set image devops-info-bg-devops-info-service devops-info-service=haruyume/devops-info-service:v2

# Check status
$ kubectl argo rollouts get rollout devops-info-bg-devops-info-service
```

**Output:**
```
Name:            devops-info-bg-devops-info-service
Namespace:       default
Status:          ॥ Paused
Message:         BlueGreenPause
Strategy:        BlueGreen
Images:          haruyume/devops-info-service:latest (stable, active)
                 haruyume/devops-info-service:v2 (preview)
Replicas:
  Desired:       3
  Current:       6
  Updated:       3
  Ready:         3
  Available:     3

NAME                                                            KIND        STATUS     AGE  INFO
⟳ devops-info-bg-devops-info-service                            Rollout     ॥ Paused   67s  
├──# revision:2                                                                             
│  └──⧉ devops-info-bg-devops-info-service-6df7cc7c69           ReplicaSet  ✔ Healthy  21s  preview
│     ├──□ devops-info-bg-devops-info-service-6df7cc7c69-5zrqq  Pod         ✔ Running  21s  ready:1/1
│     ├──□ devops-info-bg-devops-info-service-6df7cc7c69-6pmwk  Pod         ✔ Running  21s  ready:1/1
│     └──□ devops-info-bg-devops-info-service-6df7cc7c69-nl47n  Pod         ✔ Running  21s  ready:1/1
└──# revision:1                                                                             
   └──⧉ devops-info-bg-devops-info-service-7486f9b7d4           ReplicaSet  ✔ Healthy  67s  stable,active
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-w6rzj  Pod         ✔ Running  67s  ready:1/1
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-x6b8z  Pod         ✔ Running  67s  ready:1/1
      └──□ devops-info-bg-devops-info-service-7486f9b7d4-zpppg  Pod         ✔ Running  67s  ready:1/1
```

**Key Observations:**
- **6 total pods running** (3 blue + 3 green)
- Blue (revision 1) pods are **stable, active** - receiving production traffic
- Green (revision 2) pods are **preview** - accessible via preview service
- Traffic is **NOT split** - all production traffic goes to active (blue)

**Service Selectors During Preview:**

```bash
# Active service selector (production traffic)
$ kubectl get svc devops-info-bg-devops-info-service -o yaml | grep -A 3 selector
  selector:
    app.kubernetes.io/instance: devops-info-bg
    app.kubernetes.io/name: devops-info-service
    rollouts-pod-template-hash: 7486f9b7d4  # Blue version

# Preview service selector (test traffic)
$ kubectl get svc devops-info-bg-devops-info-service-preview -o yaml | grep -A 3 selector
  selector:
    app.kubernetes.io/instance: devops-info-bg
    app.kubernetes.io/name: devops-info-service
    rollouts-pod-template-hash: 6df7cc7c69  # Green version
```

### Testing Preview Environment

```bash
# Test active (blue) version
kubectl port-forward svc/devops-info-bg-devops-info-service 8080:80
# Visit http://localhost:8080

# Test preview (green) version
kubectl port-forward svc/devops-info-bg-devops-info-service-preview 8081:80
# Visit http://localhost:8081
```

### Promotion to Active

```bash
# Promote green to active
$ kubectl argo rollouts promote devops-info-bg-devops-info-service
rollout 'devops-info-bg-devops-info-service' promoted
```

**Output After Promotion:**
```
Name:            devops-info-bg-devops-info-service
Namespace:       default
Status:          ✔ Healthy
Strategy:        BlueGreen
Images:          haruyume/devops-info-service:v2 (stable, active)
Replicas:
  Desired:       3
  Current:       3
  Updated:       3
  Ready:         3
  Available:     3

NAME                                                            KIND        STATUS         AGE   INFO
⟳ devops-info-bg-devops-info-service                            Rollout     ✔ Healthy      2m8s  
├──# revision:2                                                                                  
│  └──⧉ devops-info-bg-devops-info-service-6df7cc7c69           ReplicaSet  ✔ Healthy      82s   stable,active
│     ├──□ devops-info-bg-devops-info-service-6df7cc7c69-5zrqq  Pod         ✔ Running      82s   ready:1/1
│     ├──□ devops-info-bg-devops-info-service-6df7cc7c69-6pmwk  Pod         ✔ Running      82s   ready:1/1
│     └──□ devops-info-bg-devops-info-service-6df7cc7c69-nl47n  Pod         ✔ Running      82s   ready:1/1
└──# revision:1                                                                                  
   └──⧉ devops-info-bg-devops-info-service-7486f9b7d4           ReplicaSet  • ScaledDown   2m8s  
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-w6rzj  Pod         ◌ Terminating  2m8s  ready:1/1
      ├──□ devops-info-bg-devops-info-service-7486f9b7d4-x6b8z  Pod         ◌ Terminating  2m8s  ready:1/1
      └──□ devops-info-bg-devops-info-service-7486f9b7d4-zpppg  Pod         ◌ Terminating  2m8s  ready:1/1
```

**Key Observations:**
- **Instant traffic switch** - active service selector updated immediately
- Green pods (revision 2) now marked as **stable, active**
- Blue pods (revision 1) being terminated
- Zero downtime during switchover

### Instant Rollback

Blue-Green deployments support instant rollback because the old version (blue) remains running until the scaledown delay period:

```bash
# If issues detected, rollback before blue pods are terminated
$ kubectl argo rollouts undo devops-info-bg-devops-info-service
```

This switches traffic back to blue instantly.

---

## Strategy Comparison

### Canary vs Blue-Green

| Aspect | Canary | Blue-Green |
|--------|--------|------------|
| **Traffic Shift** | Gradual (20% → 40% → 60% → 80% → 100%) | Instant (0% → 100%) |
| **Resource Usage** | Efficient (pods scaled gradually) | Higher (2x pods during deployment) |
| **Testing Window** | Continuous monitoring during rollout | Test in preview environment before switch |
| **Rollback Speed** | Gradual (traffic shifts back) | Instant (selector switch) |
| **Risk Level** | Lower (gradual exposure) | Higher (all-or-nothing) |
| **Complexity** | More steps, longer process | Simpler, faster |
| **Use Cases** | - Microservices<br>- APIs<br>- Backend services | - Frontend apps<br>- Major releases<br>- Database-heavy apps |

### When to Use Each Strategy

**Use Canary When:**
- You want to gradually expose users to new features
- You have good monitoring/metrics in place
- You can tolerate longer deployment times
- The service can handle mixed versions simultaneously
- You want to catch issues affecting small percentage of users

**Use Blue-Green When:**
- You need instant rollback capability
- You want to test fully before switching traffic
- You can afford 2x resources during deployment
- You have database migrations or schema changes
- You need deterministic deployment windows (e.g., maintenance windows)

---

## CLI Commands Reference

### Rollout Management

```bash
# Get rollout status
kubectl argo rollouts get rollout <rollout-name>

# Watch rollout in real-time
kubectl argo rollouts get rollout <rollout-name> --watch

# List all rollouts
kubectl argo rollouts list rollouts

# Describe rollout
kubectl describe rollout <rollout-name>
```

### Rollout Control

```bash
# Promote to next step (canary) or to active (blue-green)
kubectl argo rollouts promote <rollout-name>

# Abort a rollout
kubectl argo rollouts abort <rollout-name>

# Retry an aborted rollout
kubectl argo rollouts retry rollout <rollout-name>

# Undo rollout (rollback to previous version)
kubectl argo rollouts undo <rollout-name>

# Pause a rollout
kubectl argo rollouts pause <rollout-name>

# Resume a paused rollout
kubectl argo rollouts resume <rollout-name>
```

### Image Management

```bash
# Update rollout image
kubectl argo rollouts set image <rollout-name> <container>=<image>:<tag>

# Example
kubectl argo rollouts set image my-rollout app=nginx:1.19
```

### Rollout History

```bash
# View rollout history
kubectl argo rollouts history <rollout-name>

# Rollback to specific revision
kubectl argo rollouts undo <rollout-name> --to-revision=2
```

### Dashboard

```bash
# Start dashboard (port-forward)
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100

# Access at http://localhost:3100
```

### Troubleshooting

```bash
# Get rollout events
kubectl get events --field-selector involvedObject.name=<rollout-name>

# View rollout logs
kubectl logs -l app=<app-name>

# Check replicaset details
kubectl describe replicaset <replicaset-name>

# View controller logs
kubectl logs -n argo-rollouts -l app.kubernetes.io/name=argo-rollouts
```

---

## Helm Integration

### Values File Configuration

**Canary Strategy (`values.yaml`):**

```yaml
rollout:
  strategy: "canary"
  blueGreen:
    autoPromotionEnabled: false
```

**Blue-Green Strategy (`values-bluegreen.yaml`):**

```yaml
rollout:
  strategy: "blueGreen"
  blueGreen:
    autoPromotionEnabled: false
    # autoPromotionSeconds: 30
```

### Deployment Commands

```bash
# Install with canary strategy
helm install my-app ./chart --values values.yaml

# Install with blue-green strategy
helm install my-app-bg ./chart --values values-bluegreen.yaml

# Update image (use kubectl argo rollouts instead of helm upgrade for blue-green)
kubectl argo rollouts set image my-app-bg app=myimage:v2
```

---

## Summary

Argo Rollouts provides powerful progressive delivery capabilities:

1. **Canary Deployments**: Gradual traffic shifting with automatic progression and manual gates
2. **Blue-Green Deployments**: Instant traffic switching with preview environments
3. **Flexible Strategies**: Choose based on your application requirements and risk tolerance
4. **Easy Rollbacks**: Quick recovery from failed deployments
5. **Helm Integration**: Seamless integration with existing Helm charts

**Key Takeaways:**
- Canary is ideal for gradual, low-risk rollouts
- Blue-Green is perfect for instant switches with full testing
- Both strategies support manual and automated workflows
- Dashboard provides real-time visualization
- CLI tools offer comprehensive control

---

## Resources

- [Argo Rollouts Documentation](https://argoproj.github.io/argo-rollouts/)
- [Canary Strategy Guide](https://argoproj.github.io/argo-rollouts/features/canary/)
- [Blue-Green Strategy Guide](https://argoproj.github.io/argo-rollouts/features/bluegreen/)
- [kubectl Plugin](https://argoproj.github.io/argo-rollouts/features/kubectl-plugin/)
