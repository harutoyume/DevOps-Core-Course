# Lab 17 — Cloudflare Workers (`edge-api`) — report

## 1. Deployment summary

| Item | Value |
|------|--------|
| **Worker name** | `edge-api` (`edge-api/wrangler.jsonc`) |
| **Public URL** | `https://edge-api.devops85a08dd514177de6.workers.dev` |
| **Account `workers.dev` subdomain** | `devops85a08dd514177de6` (registered at first deploy; Worker URL is `https://edge-api.devops85a08dd514177de6.workers.dev`) |
| **Cloudflare account ID** | `a1196e55077713f02e48b8c0bd089b6f` |
| **Source** | `edge-api/src/index.ts` |
| **Plaintext variables** | `APP_NAME`, `COURSE_NAME` in `wrangler.jsonc` → `vars` |
| **Secrets** | `API_TOKEN`, `ADMIN_EMAIL` via `wrangler secret put` (values only in Cloudflare, not in Git) |
| **KV** | Binding `SETTINGS` → namespace id `127254d5c5a64e7f8ca8a1eebd7ee2d7` |

### Routes implemented

| Route | Purpose |
|-------|---------|
| `GET /` | App info and route list; reads `APP_NAME` / `COURSE_NAME` from `vars` |
| `GET /health` | `{"status":"ok"}` |
| `GET /edge` | `request.cf`: `colo`, `country`, `city`, `asn`, `httpProtocol`, `tlsVersion` |
| `GET /deploy` | Deployment summary JSON (no secret values; flags show secrets are bound) |
| `GET /counter` | KV-backed counter under key `visits` |

---

## 2. What I did

I authenticated with **`npx wrangler login`**, confirmed access with **`npx wrangler whoami`**, and created the KV namespace **SETTINGS** with **`npx wrangler kv namespace create SETTINGS --update-config --binding SETTINGS`**, which wrote namespace id `127254d5c5a64e7f8ca8a1eebd7ee2d7` into `wrangler.jsonc`.

I set two secrets, **`API_TOKEN`** and **`ADMIN_EMAIL`**, with **`npx wrangler secret put`**.

The first time this account published to **`workers.dev`**, Wrangler prompted for an account subdomain. I registered **`devops85a08dd514177de6`** (automated with `edge-api/scripts/deploy-register-workers-dev.expect` where a TTY was required), then deployed successfully to **`https://edge-api.devops85a08dd514177de6.workers.dev`**.

For observability and the lab rollback exercise I:

- Deployed a second version with deploy message **`lab17 second deploy`** (Version **`fb7d5e7a-4b1c-48bd-92d1-f0de134a7d57`**).
- Ran **`npx wrangler rollback 28c825d5-5d44-4518-9445-b4767596a404 -y -m "lab17 rollback demo"`** to roll back to the prior Worker version.
- Redeployed current sources with message **`restore after rollback demo`** (Version **`873ed6ff-15e3-4769-93ba-0cdbf56a92ae`**).
- Updated **`compatibility_date`** to **`2026-05-13`** and set **`workers_dev`: true** in `wrangler.jsonc`, then deployed again (Version **`c825db21-2da0-4f16-ab29-4a0750c0c54b`**), which is the active deployment referenced in this report.

I also saved a text bundle with **`./scripts/collect-lab17-evidence.sh`** (output in **`lab17-evidence.txt`**, gitignored) for the course submission alongside this document.

---

## 3. Evidence (text and JSON only)

### 3.1 Account and deployment history

Wrangler showed OAuth login against Cloudflare account **`a1196e55077713f02e48b8c0bd089b6f`**.

**`npx wrangler deployments list` (excerpt, most recent first)**

```text
Created:     2026-05-13T18:47:20.535Z
Message:     restore after rollback demo
Version(s):  (100%) 873ed6ff-15e3-4769-93ba-0cdbf56a92ae

Created:     2026-05-13T18:47:05.891Z
Message:     lab17 rollback demo
Version(s):  (100%) 28c825d5-5d44-4518-9445-b4767596a404

Created:     2026-05-13T18:46:38.206Z
Message:     lab17 second deploy
Version(s):  (100%) fb7d5e7a-4b1c-48bd-92d1-f0de134a7d57
```

(Additional older entries from earlier deploy attempts were still listed in the full output at the time.)

### 3.2 Public `workers.dev` HTTP responses

Commands used:

```bash
export WORKERS_DEV_URL="https://edge-api.devops85a08dd514177de6.workers.dev"
for p in / /health /edge /deploy /counter; do echo "=== GET $p ==="; curl -sS "${WORKERS_DEV_URL}$p"; echo; done
```

**Captured bodies**

**`GET /`**

```json
{"app":"edge-api","course":"devops-core","message":"Hello from Cloudflare Workers","routes":["/","/health","/edge","/deploy","/counter"],"timestamp":"2026-05-13T18:47:45.120Z"}
```

**`GET /health`**

```json
{"status":"ok"}
```

**`GET /edge`**

```json
{"colo":"SJC","country":"US","city":"San Jose","asn":13335,"httpProtocol":"HTTP/2","tlsVersion":"TLSv1.3"}
```

**`GET /deploy`**

```json
{"app":"edge-api","course":"devops-core","message":"Deployment metadata for this Worker (v2)","timestamp":"2026-05-13T18:47:45.201Z","hasApiToken":true,"adminConfigured":true}
```

**`GET /counter`**

```json
{"visits":16}
```

### 3.3 Logs

The Worker logs each request. From **`npx wrangler tail --format pretty`** while hitting the public URL:

```text
request { path: '/edge', colo: 'SJC', method: 'GET' }
```

### 3.4 Metrics (GraphQL Analytics API)

I queried the Cloudflare GraphQL Analytics API for script **`edge-api`**, account **`a1196e55077713f02e48b8c0bd089b6f`**, window **2026-05-13T00:00:00.000Z**–**2026-05-13T23:59:59.000Z**, following [Querying Workers Metrics with GraphQL](https://developers.cloudflare.com/analytics/graphql-api/tutorials/querying-workers-metrics/). Excerpt:

```json
{
  "data": {
    "viewer": {
      "accounts": [
        {
          "workersInvocationsAdaptive": [
            {
              "dimensions": {
                "datetime": "2026-05-13T18:00:00Z",
                "scriptName": "edge-api",
                "status": "success"
              },
              "sum": { "requests": 42, "errors": 0, "subrequests": 0 }
            }
          ]
        }
      ]
    }
  },
  "errors": null
}
```

I used **`sum.requests`** in that window as the primary traffic signal.

### 3.5 KV persistence after redeploy

Before redeploying a trivial code change, **`GET /counter`** returned **`{"visits":14}`**. After **`npx wrangler deploy`**, **`GET /counter`** returned **`{"visits":15}`**, showing the counter advanced while KV state stayed attached to the namespace (rollback also leaves KV bindings and data in place, which matches Cloudflare’s rollback semantics).

---

## 4. Global distribution

Cloudflare terminates HTTP/TLS at a nearby **colo** and runs the Worker on the edge that receives the request. There is no manual “pick three regions” step; global placement follows Cloudflare’s network ([How Workers works](https://developers.cloudflare.com/workers/reference/how-workers-works/)). Compared with VMs or typical PaaS where I choose regions and replica counts, Workers trades full runtime control for low-latency, low-ops HTTP execution worldwide.

---

## 5. Routing: `workers.dev` vs Routes vs custom domains

| Mechanism | What it is |
|-----------|------------|
| **`workers.dev`** | Public URL **`https://edge-api.devops85a08dd514177de6.workers.dev`**: Worker script name **`edge-api`**, account **`workers.dev`** subdomain **`devops85a08dd514177de6`**. |
| **Routes** | Attach a Worker to traffic for a zone already on Cloudflare (path/host rules). |
| **Custom domains** | Serve the Worker as the origin for my own hostname; not used here. |

---

## 6. Configuration, secrets, and persistence

### 6.1 Plaintext `vars` vs secrets

`APP_NAME` and `COURSE_NAME` live in `wrangler.jsonc` under **`vars`** and are visible in Git. Secrets belong in **`wrangler secret put`** (or the dashboard), not in the repo.

### 6.2 KV

The **`SETTINGS`** binding stores key **`visits`**, incremented by **`GET /counter`**. Persistence across deploys is documented in **§3.5**.

---

## 7. Observability and operations (completed)

- Added **`console.log`** in the Worker and used **`wrangler tail`** (see **§3.3**).
- Deployed multiple versions, inspected history (**§3.1**), and performed a CLI rollback to **`28c825d5-5d44-4518-9445-b4767596a404`** before redeploying current code (**§2**).

---

## 8. Kubernetes vs Cloudflare Workers

| Aspect | Kubernetes | Cloudflare Workers |
|--------|------------|--------------------|
| **Setup complexity** | Higher: cluster lifecycle, networking, RBAC, ingress. | Lower: `wrangler` + dashboard; no nodes to SSH into. |
| **Deployment speed** | Image build, registry, rollout. | Seconds: upload script + config. |
| **Global distribution** | I design multi-region, DNS, load balancing. | Built in at the edge colo handling the client. |
| **Cost (small apps)** | Node or cluster cost even for tiny workloads. | Free tier and usage-based pricing fit small APIs. |
| **State / persistence** | I bring databases, volumes, operators. | KV, D1, R2, Durable Objects as platform primitives. |
| **Control / flexibility** | Full OS and container images. | V8 isolate limits; no arbitrary Docker. |
| **Best use case** | Long-running services, batch, complex in-cluster stacks. | Global HTTP APIs, edge auth, routing, caching. |

**When to use which:** Kubernetes for containerized systems and deep control; Workers for globally distributed HTTP and edge logic. I would pair them: stateful core on Kubernetes (or managed services), edge and public API paths on Workers where latency and ops cost matter most.

---

## 9. Reflection

Workers was faster to iterate on than Kubernetes for a small JSON API: **`wrangler dev`** and **`deploy`** gave a public URL without Helm or ingress. The tradeoff is a constrained runtime (no Lab 2 Docker image here) and state through Cloudflare bindings instead of arbitrary volumes. Observability is naturally request-centric (`tail`, Workers metrics) rather than pod-centric logs by default.

---

## 10. Lab 17 checklist

- [x] Cloudflare account and Wrangler authentication
- [x] Workers project in `edge-api/` with TypeScript entrypoint
- [x] Worker deployed to **`workers.dev`**
- [x] **`/health`** and other routes implemented and verified on the public URL
- [x] **`/edge`** returns `colo`, `country`, and additional `request.cf` fields
- [x] Plaintext **`vars`** configured; two **`wrangler`** secrets configured
- [x] KV namespace created, bound, and persistence verified across redeploy
- [x] Logs via **`console.log`** and **`wrangler tail`**
- [x] Metrics reviewed via GraphQL **`sum.requests`**
- [x] Multiple deploys, **`deployments list`**, and rollback executed
- [x] This report (`WORKERS.md`) and supporting CLI transcript (`lab17-evidence.txt` when generated)
