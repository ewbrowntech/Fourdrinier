import { useCallback, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { api } from '../api'
import type { ServerRead } from '../api'

function ServersPage() {
  const [servers, setServers] = useState<ServerRead[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadServers = useCallback(async () => {
    setLoadError(null)
    try {
      setServers(await api.listServers())
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load servers.')
    }
  }, [])

  useEffect(() => {
    void loadServers()
  }, [loadServers])

  return (
    <>
      <div className="page-head">
        <h1>
          Servers
          {servers !== null && servers.length > 0 && (
            <span className="count">{servers.length}</span>
          )}
        </h1>
        <Link className="btn primary" to="/servers/new">
          Create server
        </Link>
      </div>

      {loadError && (
        <p className="board-error" role="alert">
          {loadError}{' '}
          <button type="button" className="btn small" onClick={() => void loadServers()}>
            Retry
          </button>
        </p>
      )}

      {servers !== null && servers.length === 0 && (
        <div className="empty">
          <svg className="empty-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 6l8-3 8 3-8 3-8-3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M4 12l8 3 8-3M4 18l8 3 8-3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
          <h2>No server plans yet</h2>
          <p>
            Save a Pumpkin server now. You can choose where to deploy it in a later step.
          </p>
          <Link className="btn primary" to="/servers/new">
            Create your first server
          </Link>
        </div>
      )}

      {servers !== null && servers.length > 0 && (
        <ul className="server-board">
          {servers.map((server) => (
            <li key={server.id}>
              <Link className="server-row" to="/servers/$serverId" params={{ serverId: server.id }}>
                <span className="server-cube" aria-hidden="true">
                  <span />
                </span>
                <span className="server-main">
                  <span className="host-name">{server.name}</span>
                  <span className="type-tag">Pumpkin</span>
                </span>
                <span className="server-status">
                  <span className="pill unassigned">Not deployed</span>
                </span>
                <span className="server-meta">
                  Minecraft {server.minecraft_version} · generation {server.spec_generation}
                </span>
                <span className="host-chevron" aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export default ServersPage
