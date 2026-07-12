# Kubernetes Host Configuration

This document describes how Fourdrinier manages Kubernetes clusters (k3s-focused): the authentication model, data model, credential handling, and the HTTP API. It is the Kubernetes counterpart of [docker-host-configuration.md](docker-host-configuration.md).

## Overview

A **Kubernetes host** is a cluster registered with an API server URL, the cluster CA certificate, and a **ServiceAccount bearer token**. The backend talks to the Kubernetes REST API directly over HTTPS (httpx) — no kubeconfig files, no exec plugins, no kubectl.

Design decisions:

- **ServiceAccount token auth, not client certificates.** The k3s admin kubeconfig carries a `cluster-admin` client cert that cannot be revoked (Kubernetes checks no CRLs) and expires yearly. A dedicated ServiceAccount is namespace-scoped, revocable (`kubectl delete secret`), and auditable — its identity shows up in API-server logs as `system:serviceaccount:fourdrinier:fourdrinier`.
- **Explicit CA trust, not TOFU.** k3s serves TLS from a self-signed cluster CA, so the CA cert is a required registration input (the Docker model's TOFU host-key pinning has no useful analog here — verification without the CA is impossible). Every request verifies the server certificate against the stored CA only; hostname checking stays on.
- **Namespace-scoped.** Each host row carries a `namespace` (default `fourdrinier`). All permissions granted by the bootstrap manifest, and all future workload operations, are confined to it.

## Cluster bootstrap

Apply the manifest once per cluster (as an admin):

```bash
kubectl apply -f deploy/kubernetes/fourdrinier-bootstrap.yaml
```

It creates:

| Object | Purpose |
|--------|---------|
| Namespace `fourdrinier` | Everything fourdrinier touches lives here |
| ServiceAccount `fourdrinier` | The identity fourdrinier authenticates as |
| Secret `fourdrinier-token` (`kubernetes.io/service-account-token`) | Long-lived bearer token bound to the ServiceAccount |
| Role + RoleBinding `fourdrinier` | Namespace-scoped permissions: deployments/statefulsets, services, PVCs, configmaps/secrets, pod delete/logs/exec, events |

Then extract the three registration inputs (the token controller populates the Secret asynchronously — allow a moment after apply):

```bash
# bearer token (a JWT)
kubectl -n fourdrinier get secret fourdrinier-token -o jsonpath='{.data.token}' | base64 -d

# cluster CA certificate (PEM)
kubectl -n fourdrinier get secret fourdrinier-token -o jsonpath='{.data.ca\.crt}' | base64 -d

# API server URL
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
```

> **k3s SAN note:** if you register the cluster by an address that is not in the API server certificate's SANs (common when reaching a homelab box by a LAN IP), TLS verification fails with `409`. Add the address with k3s's `--tls-san` server flag.

**Revocation:** `kubectl -n fourdrinier delete secret fourdrinier-token` invalidates the token immediately. Re-create the Secret (re-apply the manifest) to issue a new one.

**Token rotation in fourdrinier** is currently delete-and-re-register; an update endpoint is future work.

## Data model

`kubernetes_hosts` is a sibling of `docker_hosts` (no shared table):

| Column | Notes |
|--------|-------|
| `id`, `name` (unique), `enabled`, `labels`, `last_seen_at`, `created_at`, `updated_at` | Same conventions as `docker_hosts` |
| `api_url` | `https://…` only, validated at create |
| `ca_cert_pem` | Plaintext PEM — public material, validated as parseable X.509 at create |
| `token_encrypted` | Fernet token of the bearer token (same `ENCRYPTION_KEY` handling as SSH private keys) |
| `namespace` | RFC 1123 label, default `fourdrinier` |

Names are unique **across both host tables** (enforced at the API layer), so the merged `/hosts` listing is unambiguous.

## Credential handling

- The bearer token is encrypted at rest with Fernet (`ENCRYPTION_KEY`), decrypted only in memory for the duration of a request, and **never returned by any endpoint** — `KubernetesHostRead` exposes neither the token nor the CA PEM.
- A missing/invalid `ENCRYPTION_KEY` surfaces as `503`, exactly as for keypairs.

## API

Kubernetes hosts share the unified `/api/v1/hosts` surface with Docker hosts. Payloads are discriminated on `type`; requests without a `type` field are treated as `"docker"` for backward compatibility.

| Method | Path | Behavior |
|--------|------|----------|
| POST | `/hosts` | Register a host. `{"type": "kubernetes", ...}` selects this model. `409` duplicate name (either type); `422` non-https URL, unparseable CA PEM, or invalid namespace; `503` encryption key unconfigured |
| GET | `/hosts` | Merged list, sorted by name. `?type=docker` / `?type=kubernetes` filters |
| GET | `/hosts/{id}` | Fetch one host (either type) |
| DELETE | `/hosts/{id}` | `204` |
| POST | `/hosts/{id}/ping` | Validate connectivity, authentication, identity, and RBAC |

Create payload:

```json
{
  "type": "kubernetes",
  "name": "k3s-basement",
  "api_url": "https://192.168.1.40:6443",
  "ca_cert_pem": "-----BEGIN CERTIFICATE-----\n…",
  "token": "eyJhbGciOiJSUzI1NiIs…",
  "namespace": "fourdrinier",
  "labels": {"env": "homelab"}
}
```

### Ping

The ping makes three calls against the cluster, all with the stored token over CA-verified TLS:

1. `GET /version` — reachability + cluster version (`gitVersion`, e.g. `v1.31.4+k3s1`)
2. `POST …/selfsubjectreviews` — who the cluster thinks we are (requires Kubernetes ≥ 1.28)
3. `POST …/selfsubjectaccessreviews` — asks "may I `create` `apps/deployments` in `namespace`?"

This distinguishes the three common setup failures — bad token, bad CA/address, and missing RBAC — instead of reporting them all as "ping failed".

Success (`200`):

```json
{
  "status": "ok",
  "type": "kubernetes",
  "latency_ms": 18.4,
  "git_version": "v1.31.4+k3s1",
  "platform": "linux/amd64",
  "username": "system:serviceaccount:fourdrinier:fourdrinier",
  "namespace": "fourdrinier",
  "can_create_deployments": true
}
```

Error mapping (`hosts/kubernetes/errors.py`):

| Condition | Typed error | Status |
|-----------|-------------|--------|
| Server cert not signed by stored CA / bad CA | `TLSVerificationError` | `409` |
| Cluster rejected the bearer token (401) | `KubernetesAuthError` | `502` |
| API server unreachable / unexpected response | `ClusterUnreachableError` | `502` |
| ServiceAccount lacks required permissions | `KubernetesRBACError` | `403` |
| Encryption key missing/changed | `EncryptionKeyError` / `DecryptionError` | `503` |

## Operational flow

1. `kubectl apply -f deploy/kubernetes/fourdrinier-bootstrap.yaml` on the cluster.
2. Extract token, CA cert, and API URL (commands above).
3. `POST /api/v1/hosts` with `type: "kubernetes"` and the three values.
4. `POST /api/v1/hosts/{id}/ping` — expect the ServiceAccount identity and a green RBAC check; `last_seen_at` is recorded.

A Bruno collection covering this flow lives in `bruno/hosts/` (`*-kubernetes-host.bru`); it reads the token and CA from `bruno/.env` (`K8S_TOKEN`, `K8S_CA_CERT`).

## Out of scope / future work

- Token rotation endpoint (currently delete + re-register)
- Deploying and managing actual workloads on registered clusters
- Background health polling (`last_seen_at` only updates on explicit ping)
- Accepting a pasted kubeconfig and extracting the credential from it

## Testing

`src/backend/tests/test_api_hosts_kubernetes.py` covers the API surface with the HTTPS layer mocked at the `_ping_cluster` boundary (so encryption round-trips and persistence run for real); `test_kubernetes_ping.py` unit-tests `_ping_cluster` against `httpx.MockTransport`, including the 401/403/SSAR-denied/TLS-failure paths. Run with `uv run pytest` in `src/backend/`.
