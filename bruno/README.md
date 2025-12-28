# Fourdrinier API - Bruno Collection

This Bruno collection contains all API endpoints for managing Minecraft servers through the Fourdrinier API.

## Getting Started

1. **Install Bruno**: Download from [https://www.usebruno.com/](https://www.usebruno.com/)
2. **Open Collection**: In Bruno, select "Open Collection" and choose this folder
3. **Set Environment**: Select the "local" environment (or create your own)
4. **Update Base URL**: If your API is not running on `http://localhost:8000`, update the `baseUrl` in the environment

## Server Lifecycle

The complete lifecycle of a Minecraft server follows this sequence:

### 1. Create Server
Create a new server entry in the database.
- **Endpoint**: `POST /servers/`
- **Request**: Provide server name, loader type, and game version
- **Response**: Returns the created server with a unique ID
- **Script**: Automatically saves the server ID to the `serverId` environment variable

### 2. List Servers (Optional)
View all servers in the system.
- **Endpoint**: `GET /servers/`
- **Purpose**: Useful for finding server IDs or checking system state

### 3. Get Server (Optional)
Retrieve details about a specific server.
- **Endpoint**: `GET /servers/{server_id}`
- **Purpose**: Verify server configuration before starting

### 4. Start Server
Launch the Minecraft server in Kubernetes.
- **Endpoint**: `POST /servers/{server_id}/start`
- **Action**: Creates Kubernetes Pod, PVC, and Service
- **Note**: Server may take a few minutes to fully start

### 5. Stop Server
Stop the running server while preserving data.
- **Endpoint**: `PUT /servers/{server_id}/stop`
- **Action**: Deletes the Pod but keeps PVC (data persists)
- **Use Case**: Temporarily shut down server to save resources

### 6. Delete Server
Permanently remove the server and all data.
- **Endpoint**: `DELETE /servers/{server_id}`
- **Action**: Deletes all Kubernetes resources and database entry
- **Warning**: This action is irreversible
- **Script**: Automatically clears the `serverId` environment variable

## Environment Variables

The collection uses these environment variables:

- `baseUrl`: API base URL (default: `http://localhost:8000`)
- `serverId`: Current server ID (automatically set when creating a server)

## Request Numbering

Requests are numbered (1-6) to indicate the typical execution order for a complete server lifecycle. However, you can run them in any order as needed.

## Example Workflow

**Complete Server Lifecycle:**

1. Run "1. Create Server" → Server ID is auto-saved to environment
2. Run "4. Start Server" → Server launches in Kubernetes
3. *(Play Minecraft on your server)*
4. Run "5. Stop Server" → Server stops but data is preserved
5. Run "4. Start Server" again → Server restarts with same data
6. Run "6. Delete Server" → Everything is deleted

**Quick Test:**

1. Run "1. Create Server"
2. Run "2. List Servers" → Verify server exists
3. Run "6. Delete Server" → Clean up

## Health Check

Use the "Health Check" endpoint to verify the API is running before starting your workflow.

## Tips

- The collection includes post-response scripts that automatically manage the `serverId` variable
- All requests include documentation in the "Docs" tab
- Response assertions are included for key endpoints
- Server data persists on the PVC between stop/start cycles
- Only delete servers when you're certain you won't need the data

## API Documentation

For more details about the API, refer to the FastAPI automatic documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
