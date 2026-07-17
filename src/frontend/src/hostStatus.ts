// Shared presentation helpers for host status, reused by the hosts list and
// the host details page.

import type { HostPingResponse, HostRead } from './api'
import type { LampState } from './components/Lamp'

export type PingUI =
  | { phase: 'testing' }
  | { phase: 'ok'; summary: string }
  | { phase: 'fail'; message: string }

export function pingSummary(result: HostPingResponse): string {
  const latency = `${result.latency_ms.toFixed(1)} ms`
  if (result.type === 'docker') {
    return `${latency} · Docker ${result.docker_version} · ${result.os}/${result.arch}`
  }
  return `${latency} · Kubernetes ${result.git_version} · namespace ${result.namespace}`
}

export function hostEndpoint(host: HostRead): string {
  if (host.type === 'docker') {
    return `${host.username}@${host.address}:${host.port}`
  }
  return host.api_url
}

export function lampState(host: HostRead, ping?: PingUI): LampState {
  if (ping?.phase === 'testing') return 'testing'
  if (ping?.phase === 'fail') return 'fault'
  if (ping?.phase === 'ok' || host.last_seen_at !== null) return 'ok'
  return 'off'
}

export const STATUS_LABELS: Record<LampState, string> = {
  testing: 'Testing',
  fault: 'Fault',
  ok: 'Verified',
  off: 'Not tested',
}

export const STATUS_PILL_CLASS: Record<LampState, string> = {
  testing: 'testing',
  fault: 'fault',
  ok: 'ok',
  off: '',
}
