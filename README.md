# Fourdrinier

A Kubernetes-based Minecraft server management platform with integrated Modrinth mod support.

## Features

- **Server Lifecycle Management** - Create, start, stop, and delete Minecraft servers via web UI
- **Modrinth Integration** - Automatic mod installation and management for Fabric servers
- **Compatibility Validation** - Prevents server startup with incompatible mods
- **Collection Imports** - Import entire mod collections from Modrinth with one click
- **Real-time Logs** - Stream server logs directly in the browser
- **Kubernetes Native** - Servers run as pods with automatic resource management

## Tech Stack

**Backend**
- FastAPI (Python)
- SQLAlchemy + SQLite
- Kubernetes Python Client
- Alembic (migrations)

**Frontend**
- React + TypeScript
- Vite
- TanStack Query
- React Router
- Tailwind CSS + shadcn/ui

**Infrastructure**
- Kubernetes
- Docker

## Quick Start

### Prerequisites

- Kubernetes cluster
- Docker
- Python 3.10+
- Node.js 18+

### Backend Setup

```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn fourdrinier.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose up
```

## Project Structure

```
fourdrinier/
├── backend/           # FastAPI backend
│   ├── fourdrinier/
│   │   ├── api/       # API endpoints
│   │   ├── db/        # Database models and schemas
│   │   ├── services/  # Business logic (Modrinth, K8s, etc.)
│   │   └── main.py    # Application entry point
├── frontend/          # React frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       └── lib/       # API clients and utilities
├── k8s/               # Kubernetes manifests
└── docs/              # Documentation
```

## Configuration

Create a [.env](backend/.env) file in the backend directory:

```env
# Kubernetes Configuration
KUBECONFIG_PATH=/path/to/kubeconfig
NAMESPACE=minecraft-servers

# Database
DATABASE_URL=sqlite+aiosqlite:///./fourdrinier.db

# Server Defaults
DEFAULT_GAME_VERSION=1.21.1
DEFAULT_LOADER=fabric
```

## Storage Configuration

### PersistentVolumeClaim Mode (Default)
By default, Fourdrinier uses Kubernetes PVCs for server data storage:
- Portable across nodes
- Configurable storage class and size
- Production-ready with proper isolation

### Host Directory Mode (Development/Debug)
For development and debugging, you can mount a host directory directly:

1. Set environment variable:
   ```bash
   MINECRAFT_HOST_DATA_DIR=/absolute/path/to/data
   ```

2. Each server creates a subdirectory: `{Server Name} ({ID})`

3. **Important notes:**
   - Directories are **preserved** after server deletion (manual cleanup required)
   - Server names with filesystem-unsafe characters are sanitized (e.g., `/` → `_`)
   - Not recommended for production multi-node clusters
   - Requires host directory to be writable by container user (UID 1000)

**Debug examples:**

For local/native development:
```bash
# Use project's tmp directory
export MINECRAFT_HOST_DATA_DIR=/home/ebrown/projects/fourdrinier/tmp
```

For docker-compose:
```bash
# Use container path (host's ./tmp is mounted to /fd/minecraft-data)
export MINECRAFT_HOST_DATA_DIR=/fd/minecraft-data
docker-compose --profile debug up
```

The docker-compose setup automatically mounts `./tmp` to `/fd/minecraft-data` inside the container, so server data will be stored in your local `tmp` directory.

### Storage Mode Comparison

| Feature | PVC Mode | hostPath Mode |
|---------|----------|---------------|
| Production ready | ✅ Yes | ❌ No |
| Multi-node support | ✅ Yes | ❌ No |
| Easy file access | ❌ No | ✅ Yes |
| Preserved on delete | ❌ No | ✅ Yes |
| Manual cleanup | ❌ No | ✅ Required |

## Documentation

- [Modrinth Integration](docs/modrinth-integration.md) - Detailed architecture and implementation
- [Kubernetes Migration](KUBERNETES_MIGRATION.md) - Migration notes and decisions

## License

See [LICENSE.md](LICENSE.md)
