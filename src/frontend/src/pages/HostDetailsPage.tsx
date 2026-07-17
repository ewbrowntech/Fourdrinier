import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { api } from '../api'
import type { HostRead, KeypairRead } from '../api'
import Lamp from '../components/Lamp'
import EditHostForm from '../components/EditHostForm'
import { PencilIcon, RefreshIcon, TrashIcon } from '../components/icons'
import {
  hostEndpoint,
  lampState,
  pingSummary,
  STATUS_LABELS,
  STATUS_PILL_CLASS,
  type PingUI,
} from '../hostStatus'

interface HostDetailsPageProps {
  hostId: string
}

interface KeypairNotice {
  keypair: KeypairRead
  hostName: string
  address: string
  username: string
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString()
}

function HostDetailsPage({ hostId }: HostDetailsPageProps) {
  const navigate = useNavigate()
  const [host, setHost] = useState<HostRead | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [ping, setPing] = useState<PingUI | undefined>(undefined)
  const [editing, setEditing] = useState(false)
  const [keypairs, setKeypairs] = useState<KeypairRead[]>([])
  const [notice, setNotice] = useState<KeypairNotice | null>(null)
  const [copied, setCopied] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [removing, setRemoving] = useState(false)

  const loadHost = useCallback(async () => {
    setLoadError(null)
    try {
      setHost(await api.getHost(hostId))
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load this host.')
    }
  }, [hostId])

  useEffect(() => {
    void loadHost()
  }, [loadHost])

  useEffect(() => {
    if (!confirmRemove) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !removing) setConfirmRemove(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [confirmRemove, removing])

  async function handlePing() {
    if (!host) return
    setPing({ phase: 'testing' })
    try {
      const result = await api.pingHost(host.id)
      setPing({ phase: 'ok', summary: pingSummary(result) })
      // A successful ping stamps last_seen_at server-side; refresh to reflect it.
      void loadHost()
    } catch (err) {
      setPing({ phase: 'fail', message: err instanceof Error ? err.message : 'Connection test failed.' })
    }
  }

  async function openEdit() {
    if (!host) return
    setEditing(true)
    try {
      setKeypairs(await api.listKeypairs())
    } catch {
      setKeypairs([])
    }
  }

  function handleUpdated(updated: HostRead, generated: KeypairRead | null) {
    setHost(updated)
    setEditing(false)
    if (generated && updated.type === 'docker') {
      setCopied(false)
      setNotice({
        keypair: generated,
        hostName: updated.name,
        address: updated.address,
        username: updated.username,
      })
    }
  }

  async function handleDelete() {
    if (!host) return
    setRemoving(true)
    setLoadError(null)
    try {
      await api.deleteHost(host.id)
      void navigate({ to: '/hosts' })
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not remove the host.')
      setRemoving(false)
      setConfirmRemove(false)
    }
  }

  async function copyPublicKey(key: string) {
    await navigator.clipboard.writeText(key)
    setCopied(true)
  }

  if (loadError && host === null) {
    return (
      <>
        <Link className="back-link" to="/hosts">
          ← Hosts
        </Link>
        <p className="board-error" role="alert">
          {loadError} <button type="button" className="btn small" onClick={() => void loadHost()}>Retry</button>
        </p>
      </>
    )
  }

  if (host === null) {
    return (
      <>
        <Link className="back-link" to="/hosts">
          ← Hosts
        </Link>
        <p className="host-endpoint">Loading…</p>
      </>
    )
  }

  const state = lampState(host, ping)

  return (
    <>
      <Link className="back-link" to="/hosts">
        ← Hosts
      </Link>

      <div className="detail-head">
        <Lamp state={state} />
        <div className="detail-title">
          <h1>{host.name}</h1>
          <span className="type-tag">{host.type === 'docker' ? 'Docker' : 'Kubernetes'}</span>
          <span className={`pill ${STATUS_PILL_CLASS[state]}`}>{STATUS_LABELS[state]}</span>
        </div>
        <div className="detail-actions">
          <button
            type="button"
            className="icon-btn"
            onClick={() => void handlePing()}
            disabled={ping?.phase === 'testing'}
            title="Test connection"
            aria-label="Test connection"
          >
            <RefreshIcon className={`icon${ping?.phase === 'testing' ? ' spin' : ''}`} />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => void openEdit()}
            disabled={editing}
            title="Edit host"
            aria-label="Edit host"
          >
            <PencilIcon className="icon" />
          </button>
          <button
            type="button"
            className="icon-btn danger"
            onClick={() => setConfirmRemove(true)}
            title="Remove host"
            aria-label="Remove host"
          >
            <TrashIcon className="icon" />
          </button>
        </div>
      </div>

      {ping?.phase === 'ok' && <p className="host-detail ok">{ping.summary}</p>}
      {ping?.phase === 'fail' && <p className="host-detail fault">{ping.message}</p>}
      {loadError && host !== null && (
        <p className="board-error" role="alert">
          {loadError}
        </p>
      )}

      {editing && (
        <EditHostForm
          host={host}
          keypairs={keypairs}
          onUpdated={handleUpdated}
          onCancel={() => setEditing(false)}
        />
      )}

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

      {!editing && (
        <dl className="detail-grid">
          <div className="detail-item">
            <dt>Endpoint</dt>
            <dd>{hostEndpoint(host)}</dd>
          </div>
          {host.type === 'docker' ? (
            <>
              <div className="detail-item">
                <dt>Address</dt>
                <dd>{host.address}</dd>
              </div>
              <div className="detail-item">
                <dt>SSH port</dt>
                <dd>{host.port}</dd>
              </div>
              <div className="detail-item">
                <dt>Username</dt>
                <dd>{host.username}</dd>
              </div>
              <div className="detail-item">
                <dt>Host key fingerprint</dt>
                <dd>{host.host_key_fingerprint ?? '—'}</dd>
              </div>
            </>
          ) : (
            <>
              <div className="detail-item">
                <dt>API URL</dt>
                <dd>{host.api_url}</dd>
              </div>
              <div className="detail-item">
                <dt>Namespace</dt>
                <dd>{host.namespace}</dd>
              </div>
            </>
          )}
          <div className="detail-item">
            <dt>Enabled</dt>
            <dd>{host.enabled ? 'Yes' : 'No'}</dd>
          </div>
          <div className="detail-item">
            <dt>Last seen</dt>
            <dd>{host.last_seen_at ? formatTimestamp(host.last_seen_at) : 'Never'}</dd>
          </div>
          <div className="detail-item">
            <dt>Created</dt>
            <dd>{formatTimestamp(host.created_at)}</dd>
          </div>
          <div className="detail-item">
            <dt>Updated</dt>
            <dd>{formatTimestamp(host.updated_at)}</dd>
          </div>
          {Object.keys(host.labels).length > 0 && (
            <div className="detail-item">
              <dt>Labels</dt>
              <dd>
                <span className="label-list">
                  {Object.entries(host.labels).map(([key, value]) => (
                    <span key={key} className="label-chip">
                      {key}={value}
                    </span>
                  ))}
                </span>
              </dd>
            </div>
          )}
        </dl>
      )}

      {confirmRemove && (
        <div
          className="modal-overlay"
          role="presentation"
          onClick={() => {
            if (!removing) setConfirmRemove(false)
          }}
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="remove-host-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="remove-host-title">Remove {host.name}?</h2>
            <p>Fourdrinier will forget this host. This cannot be undone.</p>
            <div className="form-actions">
              <button
                type="button"
                className="btn danger"
                onClick={() => void handleDelete()}
                disabled={removing}
              >
                {removing ? 'Removing…' : 'Remove host'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setConfirmRemove(false)}
                disabled={removing}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default HostDetailsPage
