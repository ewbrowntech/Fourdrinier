# Modrinth Integration

The Modrinth integration allows users to automatically install and manage Minecraft mods from the Modrinth platform for Fabric servers. This document explains the architecture and implementation.

## Overview

Modrinth integration in Fourdrinier enables:
- Automatic mod installation from Modrinth
- Collection imports (add entire mod collections at once)
- Compatibility validation (prevents incompatible mods from breaking servers)
- Rich metadata display (mod icons, descriptions, version info)

---

## Backend Architecture

### 1. Modrinth Client Service

**File:** `backend/fourdrinier/services/modrinth_client.py`

This service handles all communication with Modrinth's API v3.

#### Key Functions

- **`extract_collection_id(collection_url: str) -> str | None`**
  - Parses Modrinth collection URLs to extract IDs
  - Supports both full URLs (`https://modrinth.com/collection/Ab0s6egg`) and bare IDs
  - Uses regex pattern matching for robustness

- **`get_collection_projects(collection_id_or_url: str) -> list[str]`**
  - Fetches project list from a Modrinth collection
  - Calls Modrinth API v3 endpoint: `/collection/{id}`
  - Returns list of project slugs/IDs
  - Includes User-Agent and 10s timeout

- **`get_project_metadata(project_id: str) -> dict | None`**
  - Retrieves individual project metadata (title, description, icon_url, game_versions, loaders)
  - Handles 404s gracefully (returns None for missing projects)
  - Distinguishes between 404 (not found) and 429 (rate limits)

- **`get_multiple_projects_metadata(project_ids: list[str]) -> dict[str, dict | None]`**
  - Batch fetches metadata with rate limiting
  - Uses async semaphore (max 5 concurrent requests) to respect Modrinth's rate limits
  - Adds 0.1s delays between requests
  - Handles failures per-project without failing entire batch
  - Returns dict mapping project_id to metadata (or None if failed)

### 2. Compatibility Validator Service

**File:** `backend/fourdrinier/services/compatibility_validator.py`

Validates whether mods work with a server's configuration before startup.

#### Key Functions

- **`check_project_compatibility(metadata: dict, game_version: str, loader: str) -> tuple[bool, list[str]]`**
  - Checks if game_version exists in project's `game_versions` list
  - Checks if loader (case-insensitive) exists in project's `loaders` list
  - Returns tuple: `(compatible: bool, warnings: list[str])`
  - Provides helpful error messages listing supported versions/loaders

- **`validate_server_modrinth_projects(server, db) -> ValidationResult`**
  - Fetches metadata for all projects on a server
  - Returns comprehensive validation result with:
    - `compatible` (bool): Whether ALL projects are compatible
    - `warnings` (list[str]): User-friendly warning messages
    - `incompatible_projects` (list[dict]): Detailed incompatibility info per project
  - Handles missing projects gracefully

### 3. Database Schema

**File:** `backend/fourdrinier/db/schema.py`

#### Server Model

```python
class Server(Base):
    id: str  # primary key
    name: str
    loader: str
    game_version: str
    modrinth_projects: list[str] | None  # JSON-stored list of project slugs
```

The `modrinth_projects` field is stored as JSON, allowing flexible list management.

#### Pydantic Schemas

- **`ServerCreate`** and **`ServerUpdate`** - Include optional `modrinth_projects` field
- **`ServerResponse`** - Includes modrinth_projects for API responses
- **`ModrinthProjectEnriched`** - Includes compatibility status and warnings
- **`ModrinthProjectInfo`** - Basic project metadata (title, description, icon)
- **`ImportCollectionResponse`** - Detailed collection import results
- **`IncompatibleProject`** - Detailed incompatibility info

---

## API Layer

**File:** `backend/fourdrinier/api/servers.py`

### Core Endpoints

#### `POST /modrinth-projects/lookup`
- Takes list of project IDs/slugs
- Returns basic metadata without compatibility checks
- Used for UI enrichment in Create/Edit dialogs

#### `POST /{server_id}/import-collection`
- Accepts Modrinth collection URL
- Extracts all projects from collection
- Merges with existing projects (deduplicates)
- Validates compatibility (informative only, doesn't block)
- Returns detailed response with warnings and incompatibility details

### Server Lifecycle Integration

#### `POST /start` - Server startup with validation

1. Retrieves server configuration from database
2. For Fabric servers with projects:
   - Creates temporary Server object for validation
   - Calls `validate_server_modrinth_projects()`
   - **If incompatible mods detected:** Raises 400 HTTPException (blocks startup)
   - Prevents server crash from incompatible mods
3. Passes validated modrinth_projects to Kubernetes pod creation

#### Kubernetes Pod Configuration

The pod is created with environment variables:
- `MODRINTH_PROJECTS` - comma-separated project list
- `MODRINTH_DOWNLOAD_DEPENDENCIES` - set to "required"

The container initialization script uses these variables to download mods from Modrinth before starting the Minecraft server.

---

## Frontend Architecture

### 1. Frontend API Layer

**File:** `frontend/src/lib/api/modrinth.ts`

Direct Modrinth API client for browser-based metadata fetching with compatibility validation:

```typescript
getModrinthProjects(
  projectIds: string[],
  gameVersion: string,
  loader: string
): Promise<ModrinthProjectEnriched[]>
```

- Fetches projects directly from Modrinth API v3
- Batches requests in groups of 100
- Deduplicates project IDs
- **Performs client-side compatibility validation** against game version and loader
- Returns enriched metadata with `compatible` flag and `warnings` array
- Maps Modrinth API response fields (`title`, `description`, `icon_url`, `game_versions`, `loaders`) to internal format
- Eliminates need for backend metadata endpoint, reducing server load

### 2. UI Components

#### ServerCard

**File:** `frontend/src/components/servers/ServerCard.tsx`

- Displays server overview with mod count badge
- Shows total number of installed mods (e.g., "3 mods")
- Click through to ServerDetailPage to view full mod list with details

#### CreateServerDialog

**File:** `frontend/src/components/servers/CreateServerDialog.tsx`

- Only shows Modrinth section for Fabric loader
- Allows adding/removing individual projects
- Shows enriched project info (title, icons) via metadata lookup
- Simple manual project addition via prompt

#### InlineModrinthEditor

**File:** `frontend/src/components/servers/InlineModrinthEditor.tsx`

Full mod management interface used in server detail pages:
- Add individual projects manually
- **Import collections** - full Modrinth collection import UI:
  - Accepts collection URL
  - Calls backend `/import-collection` endpoint
  - Shows warnings/incompatibilities to user
  - Refreshes metadata display
- Shows existing projects as pills with mod icons
- **Compatibility indicators**:
  - Compatible mods: standard gray pills
  - Incompatible mods: yellow pills with warning border
- Tooltips on mod pills show:
  - Incompatibility warnings with supported versions/loaders
  - Clickable links to Modrinth mod pages
- Disables Modrinth features for non-Fabric servers
- Fetches enriched metadata directly from Modrinth API with client-side validation

#### ServerDetailPage

**File:** `frontend/src/pages/ServerDetailPage.tsx`

- Shows detailed server information
- Displays all mods as pills with mod names and icons
- **Visual compatibility feedback**: incompatible mods highlighted in yellow
- Tooltips on mod pills show warnings and provide clickable links to Modrinth
- Full inline edit capability for mod management
- Real-time server logs alongside configuration

---

## Data Flow Examples

### Creating a Server with Mods

```
User Input (CreateServerDialog)
    ↓
Form Validation (Zod schema)
    ↓
GET /modrinth-projects/lookup (for metadata display)
    ↓
POST /servers/ (with modrinth_projects list)
    ↓
Backend: Create server in DB
    ↓
Server stored with modrinth_projects JSON list
```

### Starting a Server (with Compatibility Check)

```
User clicks "Start Server"
    ↓
POST /servers/{id}/start
    ↓
Backend Validation:
  - Create temp Server object with modrinth_projects
  - Call validate_server_modrinth_projects()
  - For each project:
    - Fetch metadata from Modrinth API
    - Check game_versions compatibility
    - Check loaders compatibility
    ↓
If incompatible projects:
  - Return 400 error with details
  - Block server startup
    ↓
If all compatible:
  - Create Kubernetes Pod
  - Set MODRINTH_PROJECTS env var
  - Container downloads mods on init
  - Server starts successfully
```

### Importing a Collection

```
User enters collection URL (EditServerDialog)
    ↓
POST /servers/{id}/import-collection?collection_url=...
    ↓
Backend:
  - Extract collection ID from URL
  - GET /collection/{id} from Modrinth
  - Get list of project IDs
  - Merge with existing (deduplicate)
  - Update server.modrinth_projects in DB
  - Call validate_server_modrinth_projects()
  - Return ImportCollectionResponse with:
    - new_count
    - total_count
    - warnings
    - incompatible_projects[]
    ↓
Frontend:
  - Display warnings to user (doesn't block)
  - Update form with new project list
  - Fetch enriched metadata for display
  - Show success/warning toast
```

---

## Key Design Patterns

### 1. Informative vs Blocking Validation

- **During collection import:** Validation is informative (shows warnings but allows import)
- **During server startup:** Validation is blocking (prevents startup with incompatible mods)
- **Rationale:** Users can prepare/fix mods after import, but startup must be safe

### 2. Rate Limit Awareness

- Semaphore limiting to 5 concurrent requests
- Small delays (0.1s) between requests
- Graceful handling of 429 (rate limit) responses
- Per-project error handling in batch operations

### 3. Client-Side Validation & Metadata Loading

- Frontend fetches enriched metadata directly from Modrinth API
- **Performs compatibility validation in the browser**:
  - Checks game version against project's `game_versions` array
  - Checks loader against project's `loaders` array (case-insensitive)
  - Generates user-friendly warning messages
- Doesn't require backend metadata endpoint
- Reduces backend API load and latency
- Real-time compatibility feedback in UI with yellow warning indicators

### 4. Metadata Caching

- Frontend caches project metadata in component state
- Prevents redundant API calls when updating UI
- Local map of project_id → metadata

### 5. Graceful Degradation

- Missing projects don't fail entire operations
- Failed metadata lookups return null; component displays project ID as fallback
- Collection imports work even if some projects are deleted from Modrinth

---

## Integration Points Summary

| Component | Role | Key Integration |
|-----------|------|-----------------|
| `modrinth_client.py` | API communication | Fetches data from Modrinth v3 API (backend) |
| `compatibility_validator.py` | Validation logic | Server-side validation for startup safety |
| `start_container.py` | Deployment safety | Blocks incompatible mod startups |
| `servers.py` (API) | Business logic | Orchestrates server operations, collection imports |
| `modrinth.ts` (Frontend) | Direct API + Validation | Browser-based metadata + client-side compatibility checking |
| React Components | UI/UX | User interactions, displays mods with visual compatibility indicators |
| InlineModrinthEditor | Mod management | Editable mod pills with yellow warnings for incompatible mods |
| Tooltip Component | User experience | Shows compatibility warnings and Modrinth links |
| Database | Persistence | Stores modrinth_projects list as JSON |

---

## Security & Reliability Considerations

1. **Input Validation:** Collection URLs parsed with regex, project IDs validated
2. **Rate Limiting:** Respects Modrinth's rate limits with semaphores and delays
3. **Error Handling:** Comprehensive error handling per-project, doesn't cascade failures
4. **Timeout Protection:** 10s HTTP timeout on all Modrinth API calls
5. **Compatibility Blocking:** Prevents server startup with incompatible mods (data integrity)
6. **Data Persistence:** Projects stored as JSON in database, survives restarts

---

## Future Enhancements

Potential improvements to consider:

- Metadata caching in backend to reduce Modrinth API calls
- Support for other loaders (Forge, Quilt, NeoForge)
- Automatic mod updates when new versions are released
- Dependency resolution (automatically include required mods)
- Server-side modpack creation and sharing
- Version pinning (lock mods to specific versions)
