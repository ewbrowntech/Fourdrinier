# Host Implementation Order

Implement the host architecture dependency-first, followed by thin vertical
slices. AI can generate the structural code early, while repositories,
services, provider behavior, and consistency decisions remain manually owned
and AI-assisted.

## 1. Define the shared vocabulary

Establish the types that the other layers will import:

- `HostType`
- provider-neutral IDs and timestamps
- shared domain exceptions
- results such as `HostPingResult`
- encryption and secret-handling interfaces

## 2. Generate the host ORM models

Use AI to generate:

- `Host`
- `DockerHostDetails`
- `KubernetesHostDetails`
- one-to-one relationships and cascades
- uniqueness, foreign-key, and provider-type constraints

Manually review the relationships, constraints, and deletion behavior.

## 3. Create the database migration

Introduce the parent `hosts` table and both provider details tables. Since
backward compatibility is not required, avoid preserving the old application
model unless existing data actually depends on it.

## 4. Generate the Pydantic schemas

Create:

- `HostCreateBase`
- `DockerHostCreate`
- `KubernetesHostCreate`
- the discriminated `HostCreate` union
- provider-specific read schemas
- a discriminated read union
- list and ping response schemas

Add schema tests immediately. Cover wrong-provider fields, a missing or unknown
`type`, missing required provider fields, forbidden extra fields, and omission
of secrets from responses.

## 5. Implement `HostRepository`

Start with persistence-only operations:

- create the parent and matching details atomically
- get by ID
- get by name
- list and filter by type
- delete
- eagerly load the matching details record

This is the first substantial logic layer to implement manually.

## 6. Define the driver boundary

Add interfaces and plumbing:

- the `HostDriver` protocol
- stable driver and domain errors
- `HostDriverRegistry`
- placeholder Docker and Kubernetes drivers

Initially, the protocol should contain only `ping`. Do not add speculative
server lifecycle methods yet.

## 7. Implement host application services

Implement the use cases in this order:

1. create
2. get
3. list and filter
4. delete
5. ping

Creation enforces the matching provider details type and transaction boundary.
Ping is the first point where repository and driver orchestration meet.

## 8. Implement one provider's ping end to end

Begin with whichever provider has the strongest existing client code, likely
Docker, and wire the complete path:

```text
endpoint -> service -> repository/registry -> driver -> remote API
```

This validates the architecture before it is duplicated for another provider.

## 9. Implement the second provider's ping

Add Kubernetes through the same boundaries. If this requires changes to the
endpoint or application service, check whether provider-specific behavior has
leaked outside the driver boundary before continuing.

## 10. Replace or simplify the `/hosts` endpoints

Keep routes limited to:

- validating request schemas
- calling application services
- mapping domain errors to HTTP responses
- returning read schemas

## 11. Remove the old host persistence paths

After the replacement flow is tested, remove:

- merged provider queries
- old top-level host models
- the implicit Docker request default
- provider branches in endpoints

## 12. Design server semantics before generating server models

First resolve:

- which remote resources represent a server
- what stopped means for each provider
- which provider identifiers must be stored
- how uncertain remote success is represented
- which operations are universal and which are optional capabilities

Only then use AI to generate the server ORM models and schemas.

## 13. Add server operations as vertical slices

Implement them in this order:

1. create
2. read and observe state
3. start
4. stop
5. delete
6. reconcile

Extend `HostDriver` only when implementing an operation with defined semantics
for both providers.

## AI ownership boundary

AI can generate:

- enums and value types
- ORM models
- Pydantic schemas
- database migrations
- protocols and interfaces
- test scaffolding

Manually own, with AI assistance:

- repository behavior
- application services
- driver behavior
- transaction boundaries
- error translation
- remote consistency and reconciliation decisions

Do not generate all server models and schemas yet. The open server lifecycle
questions need to be resolved before those structures can be trusted.
