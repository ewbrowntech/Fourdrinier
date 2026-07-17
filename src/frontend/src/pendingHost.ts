// One-shot handoff for a just-created host. The registration screen lives on
// its own route, so this carries the new host (and any generated keypair) back
// to the list, where the auto-ping and "install this key" notice are shown.

import type { HostRead, KeypairRead } from './api'

export interface PendingHost {
  host: HostRead
  generatedKeypair: KeypairRead | null
}

let pending: PendingHost | null = null

export function setPendingHost(value: PendingHost): void {
  pending = value
}

export function takePendingHost(): PendingHost | null {
  const value = pending
  pending = null
  return value
}
