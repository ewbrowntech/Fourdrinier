# Kubernetes Migration Summary

## What Was Done

The Fourdrinier project has been successfully migrated from Docker to Kubernetes (k3s) for Minecraft server deployment.

### Infrastructure Changes

1. **Kubernetes Resources Created** ([k8s/](k8s/))
   - Namespace: `minecraft`
   - ServiceAccount: `fourdrinier-backend` with RBAC permissions
   - Role: `minecraft-manager` (manage Pods, PVCs, Services)
   - Secret: Long-lived ServiceAccount token
   - Automation scripts: [setup.sh](k8s/setup.sh) and [cleanup.sh](k8s/cleanup.sh)

2. **Credentials Storage**
   - Created [.k8s/](.k8s/) directory for ServiceAccount credentials
   - Added to [.gitignore](.gitignore) for security
   - Contains: `token` and `ca.crt`

### Backend Code Changes

3. **Dependencies** ([backend/pyproject.toml](backend/pyproject.toml))
   - Removed: `docker = "^7.1.0"`
   - Added: `kubernetes = "^31.0.0"`

4. **Configuration** ([backend/fourdrinier/core/config.py](backend/fourdrinier/core/config.py))
   - Added Kubernetes API settings (host, token path, CA cert, namespace)
   - Added Minecraft server resource defaults (PVC size, CPU/memory limits)
   - Removed Docker-specific config

5. **Kubernetes Client** ([backend/fourdrinier/dependencies/kubernetes_client.py](backend/fourdrinier/dependencies/kubernetes_client.py))
   - New helper module for K8s API authentication
   - Reads ServiceAccount token and CA cert
   - Returns configured CoreV1Api client

6. **Server Deployment Logic** ([backend/fourdrinier/dependencies/deploy/start_container.py](backend/fourdrinier/dependencies/deploy/start_container.py))
   - **Complete rewrite** to use Kubernetes API
   - `start_container()`: Creates Pod + PVC + LoadBalancer Service
   - `stop_container()`: Deletes Pod only (keeps PVC/Service)
   - `delete_server_resources()`: Deletes all resources (Pod, PVC, Service)
   - Idempotent operations with proper error handling

7. **API Endpoints** ([backend/fourdrinier/api/servers.py](backend/fourdrinier/api/servers.py))
   - Updated imports (removed Docker, added Kubernetes)
   - Modified endpoints to use new K8s functions
   - Removed filesystem storage path logic
   - Updated response format (pod instead of container)

8. **Application Startup** ([backend/fourdrinier/main.py](backend/fourdrinier/main.py))
   - Removed Docker SSH setup logic

### Docker Compose Changes

9. **docker-compose.yml**
   - Updated backend environment variables for Kubernetes
   - Mounted `.k8s/token` and `.k8s/ca.crt` into containers
   - Added `host.docker.internal` for k3s API access
   - Removed Docker socket and storage path mounts
   - Removed bridge-network (no longer needed)

10. **Environment Variables** ([.env](.env))
    - Added Kubernetes configuration
    - Removed Docker-specific variables

---

## Architecture Changes

### Before (Docker)
```
Backend (Docker Compose)
  ↓ Docker API
Docker Daemon
  ↓ Creates
Minecraft Server Container (itzg/minecraft-server)
  ↓ Volume Mount
Host Filesystem (/storage/{server_id})
  ↓ Port Mapping
Host Port 25565
```

### After (Kubernetes)
```
Backend (Docker Compose)
  ↓ Kubernetes API
k3s Cluster
  ↓ Creates
Pod (itzg/minecraft-server) + PVC (5Gi) + LoadBalancer Service
  ↓ k3s ServiceLB
External IP:25565
```

---

## Next Steps

### 1. Install Python Dependencies

```bash
cd backend
poetry install
```

This will install the `kubernetes` library.

### 2. Test the Migration

#### Start the backend in debug mode:
```bash
docker compose --profile debug up backend_debug
```

#### Create a test server:
```bash
curl -X POST http://localhost:8000/servers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Server",
    "loader": "paper",
    "game_version": "1.20.1"
  }'
```

Note the `server_id` from the response.

#### Start the Minecraft server:
```bash
curl -X POST http://localhost:8000/servers/{server_id}/start
```

#### Verify in Kubernetes:
```bash
kubectl get pods,pvc,svc -n minecraft
```

You should see:
- Pod: `minecraft-{server_id}`
- PVC: `minecraft-data-{server_id}`
- Service: `minecraft-svc-{server_id}` (type: LoadBalancer)

#### Get the external IP:
```bash
kubectl get svc -n minecraft
```

#### Connect Minecraft client:
Use the EXTERNAL-IP from the LoadBalancer service, port 25565.

#### Stop the server:
```bash
curl -X PUT http://localhost:8000/servers/{server_id}/stop
```

Verify Pod is deleted but PVC/Service remain:
```bash
kubectl get pods,pvc,svc -n minecraft
```

#### Delete the server:
```bash
curl -X DELETE http://localhost:8000/servers/{server_id}
```

Verify all resources deleted:
```bash
kubectl get pods,pvc,svc -n minecraft
```

### 3. Test Scenarios

- [ ] Create and start multiple servers simultaneously
- [ ] Server data persists after Pod restart (stop/start)
- [ ] PVC deleted immediately on server deletion
- [ ] LoadBalancer IPs are unique per server
- [ ] Error handling (invalid server IDs, already running, etc.)

---

## Configuration

All settings can be customized via environment variables in [.env](.env):

| Variable | Default | Description |
|----------|---------|-------------|
| `K8S_API_HOST` | `https://host.docker.internal:6443` | k3s API server endpoint |
| `MINECRAFT_IMAGE` | `itzg/minecraft-server:java17-alpine` | Container image |
| `MINECRAFT_PVC_SIZE` | `5Gi` | Persistent volume size |
| `MINECRAFT_STORAGE_CLASS` | `local-path` | k3s storage class |
| `MINECRAFT_CPU_REQUEST` | `1000m` | CPU request (1 core) |
| `MINECRAFT_CPU_LIMIT` | `2000m` | CPU limit (2 cores) |
| `MINECRAFT_MEMORY_REQUEST` | `2Gi` | Memory request |
| `MINECRAFT_MEMORY_LIMIT` | `4Gi` | Memory limit |

---

## Troubleshooting

### Backend can't connect to k3s API
```bash
# Verify credentials exist
ls -la .k8s/

# Test kubectl access
kubectl get pods -n minecraft

# Check k3s is running
sudo systemctl status k3s
```

### Pods not starting
```bash
# Check pod logs
kubectl logs -n minecraft minecraft-{server_id}

# Describe pod for events
kubectl describe pod -n minecraft minecraft-{server_id}

# Check PVC status
kubectl get pvc -n minecraft
```

### LoadBalancer pending
```bash
# k3s ServiceLB should assign IP automatically
# If pending, check k3s-servicelb pods
kubectl get pods -n kube-system | grep svclb
```

---

## Rollback

If you need to rollback to Docker:

1. Run cleanup:
```bash
./k8s/cleanup.sh
```

2. Restore files from git:
```bash
git checkout backend/pyproject.toml
git checkout backend/fourdrinier/core/config.py
git checkout backend/fourdrinier/api/servers.py
git checkout backend/fourdrinier/main.py
git checkout docker-compose.yml
git checkout .env
```

3. Restore original start_container.py and reinstall dependencies:
```bash
git checkout backend/fourdrinier/dependencies/deploy/start_container.py
cd backend && poetry install
```

---

## Files Modified

- [k8s/namespace.yaml](k8s/namespace.yaml) ✨ New
- [k8s/serviceaccount.yaml](k8s/serviceaccount.yaml) ✨ New
- [k8s/role.yaml](k8s/role.yaml) ✨ New
- [k8s/rolebinding.yaml](k8s/rolebinding.yaml) ✨ New
- [k8s/secret-token.yaml](k8s/secret-token.yaml) ✨ New
- [k8s/setup.sh](k8s/setup.sh) ✨ New
- [k8s/cleanup.sh](k8s/cleanup.sh) ✨ New
- [.gitignore](.gitignore) - Added `.k8s/`
- [backend/pyproject.toml](backend/pyproject.toml) - Updated dependencies
- [backend/fourdrinier/core/config.py](backend/fourdrinier/core/config.py) - K8s config
- [backend/fourdrinier/dependencies/kubernetes_client.py](backend/fourdrinier/dependencies/kubernetes_client.py) ✨ New
- [backend/fourdrinier/dependencies/deploy/start_container.py](backend/fourdrinier/dependencies/deploy/start_container.py) - Complete rewrite
- [backend/fourdrinier/api/servers.py](backend/fourdrinier/api/servers.py) - Updated endpoints
- [backend/fourdrinier/main.py](backend/fourdrinier/main.py) - Removed Docker setup
- [docker-compose.yml](docker-compose.yml) - K8s integration
- [.env](.env) - K8s variables

---

## Benefits of This Migration

1. **Resource Isolation**: Each Minecraft server runs in its own Pod with defined CPU/memory limits
2. **Persistent Storage**: PVCs managed by Kubernetes, better than host mounts
3. **LoadBalancing**: Each server gets its own external IP via k3s ServiceLB
4. **Declarative Management**: Servers defined as Kubernetes resources
5. **Scalability**: Can run many servers simultaneously with resource quotas
6. **Monitoring**: Can use Kubernetes-native monitoring tools (Prometheus, Grafana)
7. **No Privileged Access**: Backend doesn't need Docker socket access

---

## Support

For issues or questions:
- Check [Kubernetes manifests](k8s/)
- Review [implementation plan](/.claude/plans/woolly-toasting-deer.md)
- Check k3s logs: `sudo journalctl -u k3s -f`
