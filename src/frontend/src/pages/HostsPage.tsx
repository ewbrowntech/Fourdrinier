import { useCallback, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { api } from '../api'
import type { HostRead, KeypairRead } from '../api'
import Lamp from '../components/Lamp'
import { takePendingHost } from '../pendingHost'
import {
  hostEndpoint,
  lampState,
  pingSummary,
  STATUS_LABELS,
  STATUS_PILL_CLASS,
  type PingUI,
} from '../hostStatus'

interface KeypairNotice {
  keypair: KeypairRead
  hostName: string
  address: string
  username: string
}

function HostsPage() {
  const [hosts, setHosts] = useState<HostRead[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [notice, setNotice] = useState<KeypairNotice | null>(null)
  const [copied, setCopied] = useState(false)
  const [pings, setPings] = useState<Record<string, PingUI>>({})

  const loadHosts = useCallback(async () => {
    setLoadError(null)
    try {
      setHosts(await api.listHosts())
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load hosts.')
    }
  }, [])

  const runPing = useCallback(async (hostId: string) => {
    setPings((prev) => ({ ...prev, [hostId]: { phase: 'testing' } }))
    try {
      const result = await api.pingHost(hostId)
      setPings((prev) => ({ ...prev, [hostId]: { phase: 'ok', summary: pingSummary(result) } }))
      // A successful ping stamps last_seen_at server-side; refresh the row to reflect it.
      const refreshed = await api.getHost(hostId)
      setHosts((prev) => (prev === null ? prev : prev.map((h) => (h.id === hostId ? refreshed : h))))
    } catch (err) {
      setPings((prev) => ({
        ...prev,
        [hostId]: { phase: 'fail', message: err instanceof Error ? err.message : 'Connection test failed.' },
      }))
    }
  }, [])

  useEffect(() => {
    void loadHosts()
  }, [loadHosts])

  // Pick up a host that was just registered on the /hosts/new screen: ping it
  // and surface the generated-key notice.
  useEffect(() => {
    const pending = takePendingHost()
    if (!pending) return
    void runPing(pending.host.id)
    if (pending.generatedKeypair && pending.host.type === 'docker') {
      setCopied(false)
      setNotice({
        keypair: pending.generatedKeypair,
        hostName: pending.host.name,
        address: pending.host.address,
        username: pending.host.username,
      })
    }
  }, [runPing])

  async function copyPublicKey(key: string) {
    await navigator.clipboard.writeText(key)
    setCopied(true)
  }

  return (
    <>
      <div className="page-head">
        <h1>
          Hosts
          {hosts !== null && hosts.length > 0 && (
            <span className="count">{hosts.length}</span>
          )}
        </h1>
        <Link className="btn primary" to="/hosts/new">
          Register host
        </Link>
      </div>

      {notice && (
        <aside className="notice">
          <h2>Install the new key on {notice.hostName}</h2>
          <p>
            Fourdrinier generated the keypair <strong>{notice.keypair.name}</strong>. Append this
            public key to <code>~/.ssh/authorized_keys</code> for{' '}
            <code>
              {notice.username}@{notice.address}
            </code>
            , then test the connection.
          </p>
          <pre className="pubkey">{notice.keypair.public_key}</pre>
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => void copyPublicKey(notice.keypair.public_key)}>
              {copied ? 'Copied' : 'Copy public key'}
            </button>
            <button type="button" className="btn ghost" onClick={() => setNotice(null)}>
              Done
            </button>
          </div>
        </aside>
      )}

      {loadError && (
        <p className="board-error" role="alert">
          {loadError} <button type="button" className="btn small" onClick={() => void loadHosts()}>Retry</button>
        </p>
      )}

      {hosts !== null && hosts.length === 0 && (
        <div className="empty">
          <svg className="empty-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="2" y="4" width="20" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
            <rect x="2" y="13" width="20" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="6" cy="7.5" r="1" fill="currentColor" />
            <circle cx="6" cy="16.5" r="1" fill="currentColor" />
          </svg>
          <h2>No hosts yet</h2>
          <p>
            A host is a machine Fourdrinier runs Minecraft servers on — a box reachable over SSH
            with Docker, or a Kubernetes cluster.
          </p>
          <Link className="btn primary" to="/hosts/new">
            Register your first host
          </Link>
        </div>
      )}

      {hosts !== null && hosts.length > 0 && (
        <ul className="host-board">
          {hosts.map((host) => {
            const state = lampState(host, pings[host.id])
            return (
              <li key={host.id}>
                <Link className="host-row" to="/hosts/$hostId" params={{ hostId: host.id }}>
                  <Lamp state={state} />
                  <div className="host-main">
                    <span className="host-name">{host.name}</span>
                    <span className="type-tag">{host.type === 'docker' ? 'Docker' : 'Kubernetes'}</span>
                  </div>
                  <div className="host-status">
                    <span className={`pill ${STATUS_PILL_CLASS[state]}`}>{STATUS_LABELS[state]}</span>
                  </div>
                  <div className="host-meta">
                    <span className="host-endpoint">{hostEndpoint(host)}</span>
                    {host.last_seen_at !== null && (
                      <span className="host-detail idle">
                        last seen {new Date(host.last_seen_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <span className="host-chevron" aria-hidden="true">
                    →
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </>
  )
}

export default HostsPage
