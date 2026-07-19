// Typed client for the Fourdrinier v1 API. Shapes mirror the Pydantic
// contracts in src/backend/fourdrinier/schemas/.

const BASE = '/api/v1'

export interface HostReadBase {
  id: string
  name: string
  enabled: boolean
  labels: Record<string, string>
  last_seen_at: string | null
  created_at: string
  updated_at: string
}

export interface DockerHostRead extends HostReadBase {
  type: 'docker'
  address: string
  port: number
  username: string
  keypair_id: string
  host_key_fingerprint: string | null
}

export interface KubernetesHostRead extends HostReadBase {
  type: 'kubernetes'
  api_url: string
  namespace: string
}

export type HostRead = DockerHostRead | KubernetesHostRead

export interface DockerHostCreate {
  type: 'docker'
  name: string
  address: string
  port: number
  username: string
  keypair_id: string
}

export interface KubernetesHostCreate {
  type: 'kubernetes'
  name: string
  api_url: string
  ca_cert_pem: string
  token: string
  namespace: string
}

export type HostCreate = DockerHostCreate | KubernetesHostCreate

// Partial updates. `type` is a required discriminator that must match the
// persisted host; every other field is optional and omitted fields are left
// unchanged. Credentials (keypair_id, token, ca_cert_pem) are write-only.
export interface DockerHostUpdate {
  type: 'docker'
  name?: string
  enabled?: boolean
  labels?: Record<string, string>
  address?: string
  port?: number
  username?: string
  keypair_id?: string
}

export interface KubernetesHostUpdate {
  type: 'kubernetes'
  name?: string
  enabled?: boolean
  labels?: Record<string, string>
  api_url?: string
  ca_cert_pem?: string
  token?: string
  namespace?: string
}

export type HostUpdate = DockerHostUpdate | KubernetesHostUpdate

export interface DockerPingResponse {
  status: 'ok'
  type: 'docker'
  latency_ms: number
  docker_version: string
  api_version: string
  os: string
  arch: string
  host_key: { fingerprint: string; key_type: string; first_seen: boolean }
}

export interface KubernetesPingResponse {
  status: 'ok'
  type: 'kubernetes'
  latency_ms: number
  git_version: string
  platform: string
  username: string
  namespace: string
}

export type HostPingResponse = DockerPingResponse | KubernetesPingResponse

export type ServerRuntime = 'paper' | 'pumpkin'

export const SERVER_RUNTIMES: readonly { id: ServerRuntime; label: string }[] = [
  { id: 'paper', label: 'Paper' },
  { id: 'pumpkin', label: 'Pumpkin' },
]

export interface ServerRead {
  id: string
  name: string
  runtime: ServerRuntime
  minecraft_version: string
  cpu_millicores: number
  memory_bytes: number
  desired_state: 'running' | 'stopped'
  spec_generation: number
  created_at: string
  updated_at: string
}

export interface ServerCreate {
  name: string
  runtime: ServerRuntime
  minecraft_version?: string | null
  cpu_millicores?: number
  memory_bytes?: number
}

export interface ServerUpdate {
  name?: string
  minecraft_version?: string
  cpu_millicores?: number
  memory_bytes?: number
}

export interface KeypairRead {
  id: string
  name: string
  source: 'generated' | 'uploaded'
  algorithm: string
  public_key: string
  fingerprint: string
  created_at: string
  updated_at: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail) && body.detail.length > 0) {
        const first = body.detail[0] as { msg?: string; loc?: unknown[] }
        if (first.msg) {
          const field = Array.isArray(first.loc) ? String(first.loc.at(-1)) : ''
          detail = field ? `${field}: ${first.msg}` : first.msg
        }
      }
    } catch {
      // Non-JSON error body; keep the generic message
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  listHosts: () => request<HostRead[]>('/hosts'),
  getHost: (id: string) => request<HostRead>(`/hosts/${id}`),
  createHost: (body: HostCreate) =>
    request<HostRead>('/hosts', { method: 'POST', body: JSON.stringify(body) }),
  updateHost: (id: string, body: HostUpdate) =>
    request<HostRead>(`/hosts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteHost: (id: string) => request<void>(`/hosts/${id}`, { method: 'DELETE' }),
  pingHost: (id: string) => request<HostPingResponse>(`/hosts/${id}/ping`, { method: 'POST' }),
  listServers: () => request<ServerRead[]>('/servers'),
  getServer: (id: string) => request<ServerRead>(`/servers/${id}`),
  createServer: (body: ServerCreate) =>
    request<ServerRead>('/servers', { method: 'POST', body: JSON.stringify(body) }),
  updateServer: (id: string, body: ServerUpdate) =>
    request<ServerRead>(`/servers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteServer: (id: string) => request<void>(`/servers/${id}`, { method: 'DELETE' }),
  listRuntimeVersions: (runtime: ServerRuntime) =>
    request<string[]>(`/runtimes/${runtime}/versions`),
  listKeypairs: () => request<KeypairRead[]>('/keypairs'),
  createKeypair: (name: string, privateKey?: string) =>
    request<KeypairRead>('/keypairs', {
      method: 'POST',
      body: JSON.stringify({ name, private_key: privateKey ?? null }),
    }),
}
