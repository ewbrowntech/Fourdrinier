---
name: verify
description: Build, launch, and drive the fourdrinier backend API to verify changes end-to-end.
---

# Verifying fourdrinier backend changes

## Launch the API against a scratch DB

From `src/backend/` (env vars map to pydantic-settings fields):

```bash
export DATABASE_URL="sqlite+aiosqlite:///<scratch-dir>/verify.db"
export ENCRYPTION_KEY="$(uv run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
uv run alembic upgrade head                     # real migration path
uv run uvicorn fourdrinier.app:create_app --factory --port 8765 &
```

API base: `http://127.0.0.1:8765/api/v1`. Routers: `/keypairs`, `/hosts`.

## Flows worth driving

- **Docker host**: `POST /keypairs {"name": ...}` → `POST /hosts` (no `type` field = docker, back-compat) → ping needs a real SSH+docker target.
- **Kubernetes host**: local k3s runs as a systemd service (`systemctl is-active k3s`); user kubeconfig at `~/.kube/config` works without sudo (`/etc/rancher/k3s/k3s.yaml` is root-only). Bootstrap: `kubectl apply -f deploy/kubernetes/fourdrinier-bootstrap.yaml`, extract creds per `docs/kubernetes-host-configuration.md`, `POST /hosts` with `type: "kubernetes"`, then `POST /hosts/{id}/ping`.
- Error-path probes that work against live k3s: garbage token → 502; `kubectl -n fourdrinier delete rolebinding fourdrinier` → ping 403 (re-apply manifest to restore); valid-but-wrong CA PEM → ping 409.

## Gotchas

- `create_app` needs `--factory` with uvicorn.
- JSON-encode CA PEMs with a script, not shell interpolation (newlines).
- Bruno collection in `bruno/` mirrors these flows; secrets come from gitignored `bruno/.env`.
