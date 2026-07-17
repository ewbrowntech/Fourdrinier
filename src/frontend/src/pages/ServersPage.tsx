function ServersPage() {
  return (
    <>
      <div className="page-head">
        <h1>Servers</h1>
      </div>
      <div className="empty">
        <svg className="empty-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 6l8-3 8 3-8 3-8-3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M4 12l8 3 8-3M4 18l8 3 8-3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
        <h2>Nothing running yet</h2>
        <p>
          Servers are the Minecraft worlds Fourdrinier runs on your hosts. Once a host is
          registered, you&apos;ll create servers here — pick a host, pick a version, and
          Fourdrinier takes care of the rest.
        </p>
        <p className="empty-actions">
          <button type="button" className="btn primary" disabled title="Server management is coming soon">
            Create server
          </button>
          <span className="soon-tag">Coming soon</span>
        </p>
        <p>
          In the meantime, <a href="#/hosts">register a host</a> so there&apos;s somewhere to run
          them.
        </p>
      </div>
    </>
  )
}

export default ServersPage
