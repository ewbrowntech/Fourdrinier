function ServersPage() {
  return (
    <>
      <div className="page-head">
        <h1>Servers</h1>
      </div>
      <div className="empty-panel">
        <h2>Nothing running yet</h2>
        <p>
          Servers are the Minecraft worlds Fourdrinier runs on your hosts. Once a host is on the
          board, you&apos;ll create servers here — pick a host, pick a version, and Fourdrinier
          takes care of the rest.
        </p>
        <p>
          <button type="button" className="btn primary" disabled title="Server management is coming soon">
            Create server
          </button>
          <span className="soon-tag">coming soon</span>
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
