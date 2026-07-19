import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { api } from '../api'
import type { ServerRead } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import EditServerForm from '../components/EditServerForm'
import { PencilIcon, TrashIcon } from '../components/icons'
import { formatCpu, formatMemory } from '../serverResources'

interface ServerDetailsPageProps {
  serverId: string
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString()
}

function ServerDetailsPage({ serverId }: ServerDetailsPageProps) {
  const navigate = useNavigate()
  const [server, setServer] = useState<ServerRead | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadServer = useCallback(async () => {
    setLoadError(null)
    try {
      setServer(await api.getServer(serverId))
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load this server.')
    }
  }, [serverId])

  useEffect(() => {
    void loadServer()
  }, [loadServer])

  function handleUpdated(updated: ServerRead) {
    setServer(updated)
    setEditing(false)
  }

  async function handleDelete() {
    if (!server) return
    setDeleting(true)
    setLoadError(null)
    try {
      await api.deleteServer(server.id)
      void navigate({ to: '/servers' })
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not delete the server.')
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  if (loadError && server === null) {
    return (
      <>
        <Link className="back-link" to="/servers">← Servers</Link>
        <p className="board-error" role="alert">
          {loadError}{' '}
          <button type="button" className="btn small" onClick={() => void loadServer()}>
            Retry
          </button>
        </p>
      </>
    )
  }

  if (server === null) {
    return (
      <>
        <Link className="back-link" to="/servers">← Servers</Link>
        <p className="host-endpoint">Loading…</p>
      </>
    )
  }

  return (
    <>
      <Link className="back-link" to="/servers">← Servers</Link>

      <div className="detail-head">
        <span className="server-cube large" aria-hidden="true"><span /></span>
        <div className="detail-title">
          <h1>{server.name}</h1>
          <span className="type-tag">Pumpkin</span>
          <span className="pill unassigned">Not deployed</span>
        </div>
        <div className="detail-actions">
          <button
            type="button"
            className="icon-btn"
            onClick={() => setEditing(true)}
            disabled={editing}
            title="Edit server"
            aria-label="Edit server"
          >
            <PencilIcon className="icon" />
          </button>
          <button
            type="button"
            className="icon-btn danger"
            onClick={() => setConfirmDelete(true)}
            title="Delete server"
            aria-label="Delete server"
          >
            <TrashIcon className="icon" />
          </button>
        </div>
      </div>

      <aside className="server-plan-note">
        <span className="plan-line" aria-hidden="true" />
        <div>
          <strong>Configuration saved</strong>
          <p>No host or remote resources are attached to this server yet.</p>
        </div>
      </aside>

      {loadError && (
        <p className="board-error" role="alert">{loadError}</p>
      )}

      {editing ? (
        <EditServerForm
          server={server}
          onUpdated={handleUpdated}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <dl className="detail-grid">
          <div className="detail-item">
            <dt>Runtime</dt>
            <dd>Pumpkin <span className="experimental-tag compact">Experimental</span></dd>
          </div>
          <div className="detail-item">
            <dt>Minecraft version</dt>
            <dd>{server.minecraft_version}</dd>
          </div>
          <div className="detail-item">
            <dt>CPU allocation</dt>
            <dd>{formatCpu(server.cpu_millicores)}</dd>
          </div>
          <div className="detail-item">
            <dt>Memory allocation</dt>
            <dd>{formatMemory(server.memory_bytes)}</dd>
          </div>
          <div className="detail-item">
            <dt>Desired state</dt>
            <dd>{server.desired_state === 'running' ? 'Running' : 'Stopped'}</dd>
          </div>
          <div className="detail-item">
            <dt>Specification generation</dt>
            <dd>{server.spec_generation}</dd>
          </div>
          <div className="detail-item">
            <dt>Created</dt>
            <dd>{formatTimestamp(server.created_at)}</dd>
          </div>
          <div className="detail-item">
            <dt>Updated</dt>
            <dd>{formatTimestamp(server.updated_at)}</dd>
          </div>
          <div className="detail-item">
            <dt>Server ID</dt>
            <dd><code>{server.id}</code></dd>
          </div>
        </dl>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={`Delete ${server.name}?`}
          confirmLabel="Delete server"
          confirmingLabel="Deleting…"
          confirming={deleting}
          danger
          onConfirm={() => void handleDelete()}
          onCancel={() => {
            if (!deleting) setConfirmDelete(false)
          }}
        >
          <p>This deletes the saved configuration. No remote resources exist for this server.</p>
        </ConfirmDialog>
      )}
    </>
  )
}

export default ServerDetailsPage
