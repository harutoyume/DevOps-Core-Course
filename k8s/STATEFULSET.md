# StatefulSet Implementation

This document describes the implementation of StatefulSets for the DevOps Info Service, providing stable network identities and persistent per-pod storage.

## Overview

### StatefulSet vs Deployment

**StatefulSet** is used for stateful applications that require:
- **Stable, unique network identifiers**: Each pod gets a predictable name (e.g., `pod-0`, `pod-1`, `pod-2`)
- **Stable, persistent storage**: Each pod has its own PersistentVolumeClaim that persists across pod restarts
- **Ordered, graceful deployment and scaling**: Pods are created/deleted in order (0→1→2)

**Deployment** is better for stateless applications where:
- Pods are interchangeable with random names
- Shared storage (if any) across all replicas
- No ordering guarantees needed

### When to Use StatefulSets

StatefulSets are ideal for:
- **Databases**: MySQL, PostgreSQL, MongoDB (each instance needs its own data)
- **Message Queues**: Kafka, RabbitMQ (stable identities for cluster membership)
- **Distributed Systems**: Elasticsearch, Cassandra (persistent identity for cluster coordination)
- **Applications with persistent state**: Our visits counter where each pod maintains its own count

### Headless Services

A **headless service** (`clusterIP: None`) creates DNS records for each pod, enabling direct pod-to-pod communication:

```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
```

For example:
- `devops-info-sts-devops-info-service-0.devops-info-sts-devops-info-service-headless.default.svc.cluster.local`

This allows stable network identities that persist across pod restarts.

---

## Implementation

### Files Created

1. **statefulset.yaml** - StatefulSet definition with volumeClaimTemplates
2. **service-headless.yaml** - Headless service for stable DNS names
3. **service.yaml** - Regular NodePort service for external access (already existed)

### Key Configuration

#### StatefulSet Template

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ include "devops-info-service.fullname" . }}
spec:
  serviceName: {{ include "devops-info-service.fullname" . }}-headless
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "devops-info-service.selectorLabels" . | nindent 6 }}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "{{ .Values.persistence.accessMode }}" ]
        resources:
          requests:
            storage: {{ .Values.persistence.size }}
```

#### Headless Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "devops-info-service.fullname" . }}-headless
spec:
  clusterIP: None
  selector:
    {{- include "devops-info-service.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
```

---

## Verification

### Resource Status

```bash
$ kubectl get po,sts,svc,pvc
```

**Output:**
```
NAME                                        READY   STATUS    RESTARTS   AGE
pod/devops-info-sts-devops-info-service-0   1/1     Running   0          2m3s
pod/devops-info-sts-devops-info-service-1   1/1     Running   0          8m52s
pod/devops-info-sts-devops-info-service-2   1/1     Running   0          8m45s

NAME                                                   READY   AGE
statefulset.apps/devops-info-sts-devops-info-service   3/3     9m1s

NAME                                                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/devops-info-sts-devops-info-service            NodePort    10.106.255.60   <none>        80:30080/TCP   9m1s
service/devops-info-sts-devops-info-service-headless   ClusterIP   None            <none>        80/TCP         9m1s
service/kubernetes                                     ClusterIP   10.96.0.1       <none>        443/TCP        14d

NAME                                                               STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/data-devops-info-sts-devops-info-service-0   Bound    pvc-bfbede49-30bf-459b-a9b0-225faee51fa0   100Mi      RWO            standard       9m1s
persistentvolumeclaim/data-devops-info-sts-devops-info-service-1   Bound    pvc-f083f49b-0646-41b2-9ff8-ee49cf12a8f2   100Mi      RWO            standard       8m52s
persistentvolumeclaim/data-devops-info-sts-devops-info-service-2   Bound    pvc-039e93de-9f2b-4654-880f-d74be41268ca   100Mi      RWO            standard       8m45s
```

**Key Observations:**
- ✅ Pods have ordered names: `-0`, `-1`, `-2`
- ✅ StatefulSet shows 3/3 ready replicas
- ✅ Two services: regular NodePort + headless
- ✅ Each pod has its own PersistentVolumeClaim (per-pod storage)

---

## DNS Resolution Testing

### Test Command

```bash
$ kubectl exec -it devops-info-sts-devops-info-service-0 -- python3 -c "import socket; \
  print('Pod-0:', socket.gethostbyname('devops-info-sts-devops-info-service-0.devops-info-sts-devops-info-service-headless.default.svc.cluster.local')); \
  print('Pod-1:', socket.gethostbyname('devops-info-sts-devops-info-service-1.devops-info-sts-devops-info-service-headless.default.svc.cluster.local')); \
  print('Pod-2:', socket.gethostbyname('devops-info-sts-devops-info-service-2.devops-info-sts-devops-info-service-headless.default.svc.cluster.local'))"
```

**Output:**
```
Pod-0: 10.244.0.55
Pod-1: 10.244.0.57
Pod-2: 10.244.0.58
```

**Analysis:**
- ✅ Each pod has a stable DNS name that resolves to its cluster IP
- ✅ DNS names follow the pattern: `<pod-name>.<headless-service>.<namespace>.svc.cluster.local`
- ✅ These DNS names persist even if pods are restarted

---

## Per-Pod Storage Isolation

### Test: Writing Different Data to Each Pod

```bash
# Write different visit counts to each pod
$ kubectl exec devops-info-sts-devops-info-service-0 -- sh -c "echo 5 > /data/visits"
$ kubectl exec devops-info-sts-devops-info-service-1 -- sh -c "echo 10 > /data/visits"
$ kubectl exec devops-info-sts-devops-info-service-2 -- sh -c "echo 15 > /data/visits"
```

### Verification: Reading Data from Each Pod

```bash
$ echo "Pod-0 visits:" && kubectl exec devops-info-sts-devops-info-service-0 -- cat /data/visits
$ echo "Pod-1 visits:" && kubectl exec devops-info-sts-devops-info-service-1 -- cat /data/visits
$ echo "Pod-2 visits:" && kubectl exec devops-info-sts-devops-info-service-2 -- cat /data/visits
```

**Output:**
```
Pod-0 visits:
5
Pod-1 visits:
10
Pod-2 visits:
15
```

**Analysis:**
- ✅ Each pod maintains its own independent storage
- ✅ Data written to one pod does not affect other pods
- ✅ Each pod's PersistentVolumeClaim is unique and isolated

---

## Data Persistence Testing

### Test: Pod Deletion and Recreation

**Step 1: Delete pod-0**
```bash
$ kubectl delete pod devops-info-sts-devops-info-service-0
pod "devops-info-sts-devops-info-service-0" deleted
```

**Step 2: Wait for StatefulSet to recreate pod-0**
```bash
$ kubectl get pods
NAME                                    READY   STATUS    RESTARTS   AGE
devops-info-sts-devops-info-service-0   1/1     Running   0          100s
devops-info-sts-devops-info-service-1   1/1     Running   0          8m29s
devops-info-sts-devops-info-service-2   1/1     Running   0          8m22s
```

**Step 3: Verify data persisted**
```bash
$ kubectl exec devops-info-sts-devops-info-service-0 -- cat /data/visits
5
```

**Analysis:**
- ✅ Pod-0 was automatically recreated by the StatefulSet controller
- ✅ The new pod-0 reattached to the same PersistentVolumeClaim
- ✅ Data (value "5") persisted across pod deletion and recreation
- ✅ PVC remains bound even when pod is deleted
- ✅ StatefulSet guarantees the same PVC is used for the recreated pod

---

## How It Works

### VolumeClaimTemplates

Unlike Deployments which can only reference existing PVCs, StatefulSets use `volumeClaimTemplates` to automatically create a PVC for each pod:

```yaml
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Mi
```

This creates PVCs named: `data-<statefulset-name>-<ordinal>`

### Pod Naming

Pods are named: `<statefulset-name>-<ordinal>` where ordinal starts at 0:
- `devops-info-sts-devops-info-service-0`
- `devops-info-sts-devops-info-service-1`
- `devops-info-sts-devops-info-service-2`

### Ordered Deployment

Pods are created in order:
1. Pod-0 created and becomes Ready
2. Pod-1 created and becomes Ready
3. Pod-2 created and becomes Ready

During scale-down, pods are deleted in reverse order (2→1→0).

---

## Deployment Commands

### Install the Chart

```bash
helm install devops-info-sts k8s/devops-info-service/
```

### Verify Deployment

```bash
kubectl get statefulset
kubectl get pods
kubectl get pvc
kubectl get svc
```

### Access the Application

```bash
# Via NodePort service
minikube service devops-info-sts-devops-info-service

# Via port-forward to specific pod
kubectl port-forward pod/devops-info-sts-devops-info-service-0 8080:5000
```

### Cleanup

```bash
helm uninstall devops-info-sts
# Note: PVCs are not automatically deleted
kubectl delete pvc -l app.kubernetes.io/instance=devops-info-sts
```

---

## Key Differences from Previous Rollout Implementation

| Feature | Rollout (Lab 14) | StatefulSet (Lab 15) |
|---------|------------------|----------------------|
| **Purpose** | Progressive delivery (canary, blue-green) | Stateful applications |
| **Pod Names** | Random suffix | Ordered index |
| **Storage** | Shared or single PVC | Per-pod PVC via templates |
| **Scaling** | Any order | Ordered (0→1→2) |
| **Network Identity** | Random | Stable DNS names |
| **Use Case** | Stateless apps with safe rollout | Databases, stateful services |

**Note:** Rollouts are for deployment strategies (how you roll out updates), while StatefulSets are for application architecture (applications needing stable identity/storage).

---

## Conclusion

StatefulSets provide the necessary guarantees for running stateful applications in Kubernetes:
- ✅ Stable, predictable pod names
- ✅ Stable network identities via headless services
- ✅ Per-pod persistent storage
- ✅ Ordered deployment and scaling
- ✅ Data persistence across pod restarts

This implementation successfully demonstrates all the key features of StatefulSets, making it suitable for applications like databases, message queues, or any service requiring persistent state and stable identity.
