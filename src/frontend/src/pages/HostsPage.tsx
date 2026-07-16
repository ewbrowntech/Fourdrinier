import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { HostPingResponse, HostRead, KeypairRead } from '../api'
import Lamp from '../components/Lamp'
import type { LampState } from '../components/Lamp'
import RegisterHostForm from '../components/RegisterHostForm'

type PingUI =
  | { phase: 'testing' }
  | { phase: 'ok'; summary: string }
  | { phase: 'fail'; message: string }

interface KeypairNotice {
  keypair: KeypairRead
  hostName: string
  address: string
  username: string
}

function pingSummary(result: HostPingResponse): string {
  const latency = `${result.latency_ms.toFixed(1)} ms`
  if (result.type === 'docker') {
    return `${latency} · Docker ${result.docker_version} · ${result.os}/${result.arch}`
  }
  return `${latency} · Kubernetes ${result.git_version} · namespace ${result.namespace}`
}

function hostEndpoint(host: HostRead): string {
  if (host.type === 'docker') {
    return `${host.username}@${host.address}:${host.port}`
  }
  return host.api_url
}

function lampState(host: HostRead, ping: PingUI | undefined): LampState {
  if (ping?.phase === 'testing') return 'testing'
  if (ping?.phase === 'fail') return 'fault'
  if (ping?.phase === 'ok' || host.last_seen_at !== null) return 'ok'
  return 'off'
}

function HostsPage() {
  const [hosts, setHosts] = useState<HostRead[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [keypairs, setKeypairs] = useState<KeypairRead[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [pings, setPings] = useState<Record<string, PingUI>>({})
  const [notice, setNotice] = useState<KeypairNotice | null>(null)
  const [copied, setCopied] = useState(false)

  const loadHosts = useCallback(async () => {
    setLoadError(null)
    try {
      setHosts(await api.listHosts())
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load hosts.')
    }
  }, [])

  useEffect(() => {
    void loadHosts()
  }, [loadHosts])

  async function openForm() {
    setFormOpen(true)
    try {
      setKeypairs(await api.listKeypairs())
    } catch {
      setKeypairs([])
    }
  }

  function handleCreated(host: HostRead, generated: KeypairRead | null) {
    setHosts((prev) => [...(prev ?? []), host])
    setFormOpen(false)
    if (generated && host.type === 'docker') {
      setCopied(false)
      setNotice({
        keypair: generated,
        hostName: host.name,
        address: host.address,
        username: host.username,
      })
    }
  }

  async function handlePing(host: HostRead) {
    setPings((prev) => ({ ...prev, [host.id]: { phase: 'testing' } }))
    try {
      const result = await api.pingHost(host.id)
      setPings((prev) => ({ ...prev, [host.id]: { phase: 'ok', summary: pingSummary(result) } }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection test failed.'
      setPings((prev) => ({ ...prev, [host.id]: { phase: 'fail', message } }))
    }
  }

  async function handleDelete(host: HostRead) {
    if (!window.confirm(`Remove ${host.name}? Fourdrinier will forget this host.`)) return
    try {
      await api.deleteHost(host.id)
      setHosts((prev) => (prev ?? []).filter((h) => h.id !== host.id))
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not remove the host.')
    }
  }

  async function copyPublicKey(key: string) {
    await navigator.clipboard.writeText(key)
    setCopied(true)
  }

  return (
    <>
      <div className="page-head">
        <h1>Hosts</h1>
        {!formOpen && (
          <button type="button" className="btn primary" onClick={() => void openForm()}>
            Register host
          </button>
        )}
      </div>
      {hosts !== null && hosts.length > 0 && (
        <p className="legend" aria-hidden="true">
          <span className="lamp ok static" /> verified
          <span className="lamp off static" /> not tested
          <span className="lamp fault static" /> fault
        </p>
      )}

      {formOpen && (
        <RegisterHostForm
          keypairs={keypairs}
          onCreated={handleCreated}
          onCancel={() => setFormOpen(false)}
        />
      )}

      {notice && (
        <aside className="keypair-notice">
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
            <button type="button" className="btn quiet" onClick={() => setNotice(null)}>
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

      {hosts !== null && hosts.length === 0 && !formOpen && (
        <div className="empty-panel">
          <h2>No hosts on the board</h2>
          <p>
            A host is a machine Fourdrinier can run Minecraft servers on — a box reachable over
            SSH with Docker, or a Kubernetes cluster.
          </p>
          <button type="button" className="btn primary" onClick={() => void openForm()}>
            Register your first host
          </button>
        </div>
      )}

      {hosts !== null && hosts.length > 0 && (
        <ul className="host-board">
          {hosts.map((host, index) => {
            const ping = pings[host.id]
            return (
              <li key={host.id} className="host-row">
                <Lamp state={lampState(host, ping)} delayMs={index * 90} />
                <div className="host-id">
                  <span className="host-name">
                    {host.name}
                    <span className="type-tag">{host.type === 'docker' ? 'Docker' : 'Kubernetes'}</span>
                  </span>
                  <span className="host-endpoint">{hostEndpoint(host)}</span>
                </div>
                <div className="host-status">
                  {ping?.phase === 'ok' && <span className="ping-ok">{ping.summary}</span>}
                  {ping?.phase === 'fail' && <span className="ping-fail">{ping.message}</span>}
                  {!ping && host.last_seen_at !== null && (
                    <span className="ping-idle">
                      last seen {new Date(host.last_seen_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <div className="host-actions">
                  <button
                    type="button"
                    className="btn small"
                    onClick={() => void handlePing(host)}
                    disabled={ping?.phase === 'testing'}
                  >
                    {ping?.phase === 'testing' ? 'Testing…' : 'Test connection'}
                  </button>
                  <button type="button" className="btn small quiet" onClick={() => void handleDelete(host)}>
                    Remove
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </>
  )
}

export default HostsPage
