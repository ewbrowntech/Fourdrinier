# Modrinth Integration

The Modrinth integration allows users to automatically install and manage Minecraft content from the Modrinth platform for Fabric servers. This includes mods, datapacks, shaders, resource packs, and plugins. This document explains the architecture and implementation.

## Overview

Modrinth integration in Fourdrinier enables:
- Automatic installation of mods, datapacks, shaders, resource packs, and plugins
- Collection imports (add entire collections at once)
- Type-aware compatibility validation (prevents incompatible content from breaking servers)
- Rich metadata display (project icons, descriptions, version info)
- Separate UI sections per project type with individual counters

---

## Project Types

Fourdrinier supports five distinct Modrinth project types, each with different compatibility rules and container behavior:

| Type | Description | Game Version Check | Loader Check | Container Behavior |
|------|-------------|-------------------|--------------|-------------------|
| **mod** | Server-side mods | ✓ | ✓ | Installed as-is (e.g., `sodium`) |
| **datapack** | Data packs | ✓ | ✗ | Installed with prefix (e.g., `datapack:terralith`) |
| **shader** | Shader packs | ✓ | ✗ | **Client-side only** - excluded from container |
| **resourcepack** | Resource packs | ✓ | ✗ | **Client-side only** - excluded from container |
| **plugin** | Server plugins | ✓ | ✗ | Installed for compatible loaders (Paper, Spigot) |

### Compatibility Rules by Type

- **Mods**: Validated against both game version AND loader (e.g., must support Fabric 1.20.1)
- **All other types**: Validated against game version ONLY (loader-agnostic)

This distinction is important because:
- Datapacks work across all loaders (Vanilla, Fabric, Forge, etc.)
- Shaders and resource packs are client-side and don't depend on server loader
- Plugins have their own loader requirements handled separately

### Data Structure

Projects are stored as structured objects with type information:

**New format (current):**
```json
{
  "modrinth_projects": [
    {"id": "sodium", "type": "mod"},
    {"id": "terralith", "type": "datapack"},
    {"id": "complementary-shaders", "type": "shader"}
  ]
}
```

**Legacy format (backward compatible):**
```json
{
  "modrinth_projects": ["sodium", "lithium", "fabric-api"]
}
```

The system automatically converts legacy string arrays to the new format, defaulting to type `"mod"` for backward compatibility.

---

## Backend Architecture

### 1. Modrinth Client Service

**File:** `backend/fourdrinier/services/modrinth_client.py`

This service handles all communication with Modrinth's API v3.

#### Modrinth API v3 Field Structure

**Critical**: Modrinth API v3 uses different field names than might be expected:

| Expected Field | Actual API v3 Field | Type | Notes |
|----------------|---------------------|------|-------|
| `title` | `name` | string | Project display name |
| `project_type` | `project_types` | array | Array of types (e.g., `["mod"]`, `["resourcepack"]`) |

**Example API Response:**
```json
{
  "name": "Complementary Shaders",
  "project_types": ["shader"],
  "description": "...",
  "icon_url": "...",
  "game_versions": ["1.20.1", "1.20.2"],
  "loaders": []
}
```

The code intelligently selects the best type from the `project_types` array:
- If a project is available as both **mod** and **datapack**, and the server loader is **Fabric** or **Forge**, it will prefer **mod**
- Otherwise, it uses the first element from the array
- Uses `name` field for the project title

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
  - Retrieves individual project metadata (name, description, icon_url, game_versions, loaders, **project_type**)
  - **Extracts project_type** from Modrinth API v3 `project_types` array (first element)
  - Maps to one of: mod, datapack, shader, resourcepack, plugin
  - Defaults to "mod" if project_types field is missing or empty
  - Note: Modrinth API v3 uses `project_types` (plural, array) not `project_type` (singular)
  - Note: Modrinth API v3 uses `name` field not `title`
  - Handles 404s gracefully (returns None for missing projects)
  - Distinguishes between 404 (not found) and 429 (rate limits)

- **`get_multiple_projects_metadata(project_ids: list[str]) -> dict[str, dict | None]`**
  - **Batch fetches metadata using Modrinth's batch API endpoint**: `GET /v3/projects?ids=["id1","id2",...]`
  - Batches requests in groups of 100 (Modrinth's API limit per request)
  - Single API call per 100 projects (vastly reduces rate limit issues)
  - Handles failures per-batch without failing entire operation
  - Returns dict mapping project_id to metadata (or None if not found)

### 2. Compatibility Validator Service

**File:** `backend/fourdrinier/services/compatibility_validator.py`

Validates whether projects work with a server's configuration before startup, with type-aware compatibility rules.

#### Key Functions

- **`check_project_compatibility(metadata: dict, game_version: str, loader: str, project_type: str = "mod") -> tuple[bool, list[str]]`**
  - **Type-aware validation:**
    - **For mods**: Checks both game_version AND loader compatibility
    - **For all other types** (datapack, shader, resourcepack, plugin): Checks ONLY game_version (loader-agnostic)
  - Checks if game_version exists in project's `game_versions` list
  - Checks if loader (case-insensitive) exists in project's `loaders` list (mods only)
  - Returns tuple: `(compatible: bool, warnings: list[str])`
  - Provides helpful error messages listing supported versions/loaders

- **`validate_server_modrinth_projects(server, db) -> ValidationResult`**
  - **Handles both legacy (string array) and new (object array) formats**
  - Extracts project type from each entry (defaults to "mod" for legacy format)
  - Fetches metadata for all projects on a server
  - Passes project type to `check_project_compatibility()` for type-aware validation
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
    modrinth_projects: list[dict] | None  # JSON-stored list of project objects
```

The `modrinth_projects` field is stored as JSON with structured objects containing project ID and type.

#### Pydantic Schemas

- **`ModrinthProject`** - Project model with ID and type:
  ```python
  class ModrinthProject(BaseModel):
      id: str  # Project slug or ID
      type: str = Field(default="mod", pattern="^(mod|datapack|shader|resourcepack|plugin)$")
  ```
- **`ServerCreate`** and **`ServerUpdate`** - Include optional `modrinth_projects: list[ModrinthProject] | None`
  - Includes `@model_validator` for backward compatibility (auto-converts legacy string arrays)
- **`ServerResponse`** - Includes modrinth_projects for API responses
- **`ModrinthProjectEnriched`** - Includes compatibility status, warnings, and **project_type**
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
- **Auto-detects project types** by fetching metadata from Modrinth API
  - **Smart type selection**: If a project is available as both mod and datapack, prefers mod for Fabric/Forge servers
- Merges with existing projects (deduplicates)
- Validates compatibility with type-aware checking (informative only, doesn't block)
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
- `MODRINTH_PROJECTS` - comma-separated project list with type-specific formatting
- `MODRINTH_DOWNLOAD_DEPENDENCIES` - set to "required"

**Type-specific container behavior:**
- **Mods**: Passed as-is (e.g., `sodium,lithium,fabric-api`)
- **Datapacks**: Passed with `datapack:` prefix (e.g., `datapack:terralith,datapack:incendium`)
- **Shaders**: Excluded (client-side only, not installed in container)
- **Resource packs**: Excluded (client-side only, not installed in container)
- **Plugins**: Passed as-is (for Paper/Spigot servers)

**Example `MODRINTH_PROJECTS` value:**
```
sodium,lithium,datapack:terralith,datapack:incendium
```

The container initialization script (from [itzg/minecraft-server](https://github.com/itzg/docker-minecraft-server)) uses these variables to download content from Modrinth before starting the Minecraft server.

---

## Frontend Architecture

### 1. Frontend API Layer

**File:** `frontend/src/lib/api/modrinth.ts`

Direct Modrinth API client for browser-based metadata fetching with type-aware compatibility validation:

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
- **Extracts `project_type`** from Modrinth API v3 `project_types` array with smart selection:
  - If project available as both mod and datapack, prefers mod for Fabric/Forge loaders
  - Otherwise uses first element from array
- **Performs type-aware client-side compatibility validation:**
  - **For mods**: Checks both game version AND loader
  - **For all other types**: Checks ONLY game version (loader-agnostic)
- Returns enriched metadata with `compatible` flag, `warnings` array, and `project_type`
- Maps Modrinth API response fields (`name`, `description`, `icon_url`, `game_versions`, `loaders`, `project_types`) to internal format
- Note: Modrinth API v3 uses `name` not `title`, and `project_types` (array) not `project_type`
- Eliminates need for backend metadata endpoint, reducing server load

### 2. UI Components

#### ServerCard

**File:** `frontend/src/components/servers/ServerCard.tsx`

- Displays server overview with **individual type counters**
- Shows separate badges for each project type with count > 0:
  - "3 mods"
  - "2 datapacks"
  - "1 shader"
- Uses `countProjectsByType()` helper to group projects
- Click through to ServerDetailPage to view full project list with details

#### CreateServerDialog

**File:** `frontend/src/components/servers/CreateServerDialog.tsx`

- Only shows Modrinth section for Fabric loader
- Allows adding/removing individual projects
- Shows enriched project info (title, icons) via metadata lookup
- Simple manual project addition via prompt

#### InlineModrinthEditor

**File:** `frontend/src/components/servers/InlineModrinthEditor.tsx`

Full project management interface used in server detail pages:
- **Type-grouped display**: Projects organized into separate sections (Mods, Datapacks, Shaders, Resource Packs, Plugins)
- Add individual projects manually with **auto-detect type** from Modrinth API
  - Smart type selection: prefers mod over datapack for Fabric/Forge servers
- Allow manual type override when adding projects
- **Import collections** - full Modrinth collection import UI:
  - Accepts collection URL
  - Calls backend `/import-collection` endpoint (auto-detects types with smart selection)
  - Shows warnings/incompatibilities to user
  - Refreshes metadata display
- Shows existing projects as pills with project icons, **grouped by type**
- **Compatibility indicators**:
  - Compatible projects: standard gray pills
  - Incompatible projects: yellow pills with warning border
- Tooltips on project pills show:
  - Project summary
  - Incompatibility warnings with supported versions/loaders (type-aware)
  - Clickable links to Modrinth project pages
- Disables Modrinth features for non-Fabric servers
- Fetches enriched metadata directly from Modrinth API with type-aware client-side validation

#### ServerDetailPage

**File:** `frontend/src/pages/ServerDetailPage.tsx`

- Shows detailed server information
- **Header displays individual type counters** (e.g., "3 mods", "2 datapacks")
- Displays all projects as pills with names and icons, **organized by type**
- **Visual compatibility feedback**: incompatible projects highlighted in yellow
- Tooltips on project pills show warnings and provide clickable links to Modrinth
- Full inline edit capability for project management
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

- **Uses Modrinth's batch API** (`/v3/projects?ids=[...]`) to fetch up to 100 projects per request
- Drastically reduces API calls compared to individual requests
- Graceful handling of 429 (rate limit) responses
- Per-batch error handling without failing entire operation

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

### 6. Smart Type Selection

- Projects can be available as multiple types on Modrinth (e.g., both mod and datapack)
- Modrinth API v3 returns `project_types` as an array (e.g., `["mod", "datapack"]`)
- **Intelligent type selection based on server loader:**
  - For **Fabric/Forge** servers: Prefers `mod` over `datapack` when both available
  - Rationale: Mods provide better performance and features on modded servers
  - For other loaders or single-type projects: Uses first type from array
- Applied in both backend (collection import) and frontend (manual project add)
- Ensures optimal project type is automatically selected for the server configuration

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

## Maintenance Tools

### Fix Project Types Script

**File:** `backend/scripts/fix_project_types.py`

A one-time migration script to update existing servers with correct project types from Modrinth API.

**Usage:**
```bash
python -m scripts.fix_project_types
```

**What it does:**
1. Fetches all servers with modrinth_projects
2. For each project, fetches metadata from Modrinth API to get correct project_type
3. Updates the database with corrected types
4. Converts legacy string format to new structured format

**When to use:**
- After upgrading from a version that didn't support project types
- To fix servers that have incorrect types (e.g., shaders labeled as mods)
- To migrate from old string array format to new structured format

---

## Future Enhancements

Potential improvements to consider:

- Metadata caching in backend to reduce Modrinth API calls
- Support for other loaders (Forge, Quilt, NeoForge)
- Automatic mod updates when new versions are released
- Dependency resolution (automatically include required mods)
- Server-side modpack creation and sharing
- Version pinning (lock mods to specific versions)
