# /servers/

## create_server() [POST /servers/]
- **[000] test_create_server_000_nominal**
    - Conditions: One valid server object
    - Result: HTTP 201 - Server object returned

## list_servers() [GET /servers/]
- **[000] test_list_servers_000_nominal_no_servers**
    - Conditions: No servers in database
    - Result: HTTP 200 - []
- **[001] test_list_servers_001_nominal_two_servers**
    - Conditinos: Two servers in database
    - Result: HTTP 200 - [`server1`, `server2`]

## get_server() [GET /servers/{server_id}]
- **[000] test_get_server_000_nominal**
    - Conditions: Server1 in database, request Server1
    - Result: HTTP 200 - `server1`
- **[001] test_get_server_001_anomalous_nonexistent_server**
    - Conditions: Server1 in database, request Server2
    - Result: HTTP 404 - "Server not found"

## start_server() [POST /servers/{server_id}/start]
- **[000] test_start_server_000_nominal**
    - Conditions: Server exists in database, Kubernetes client mocked for success
    - Result: HTTP 201 - Pod created with correct name and namespace
- **[001] test_start_server_001_nominal_with_modrinth_projects**
    - Conditions: Fabric server with Modrinth projects, Kubernetes client mocked
    - Result: HTTP 201 - Pod created with MODRINTH_PROJECTS environment variable
- **[002] test_start_server_002_nominal_idempotent**
    - Conditions: Server exists, Pod already running (409 Conflict on creation)
    - Result: HTTP 201 - Returns successfully (idempotent behavior)
- **[003] test_start_server_003_anomalous_server_not_found**
    - Conditions: Request to start non-existent server
    - Result: HTTP 404 - "Server not found"
- **[004] test_start_server_004_anomalous_pvc_creation_fails**
    - Conditions: Server exists, Kubernetes PVC creation fails (non-409 error)
    - Result: HTTP 500 - RuntimeError from start_container
- **[005] test_start_server_005_anomalous_pod_creation_fails**
    - Conditions: Server exists, PVC succeeds, Pod creation fails
    - Result: HTTP 500 - RuntimeError from start_container, PVC cleaned up
- **[006] test_start_server_006_nominal_paper_loader**
    - Conditions: Paper server (no Modrinth projects)
    - Result: HTTP 201 - Pod created without MODRINTH_PROJECTS env vars