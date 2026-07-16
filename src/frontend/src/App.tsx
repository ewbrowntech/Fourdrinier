import { useEffect, useState } from 'react'
import HostsPage from './pages/HostsPage'
import ServersPage from './pages/ServersPage'

type Route = 'hosts' | 'servers'

function currentRoute(): Route {
  return window.location.hash === '#/servers' ? 'servers' : 'hosts'
}

function App() {
  const [route, setRoute] = useState<Route>(currentRoute)

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return (
    <>
      <header className="control-bar">
        <a className="brand" href="#/hosts">
          <span className="brand-lamp" aria-hidden="true" />
          <span className="brand-text">
            Fourdrinier
            <span className="brand-sub">Server mill</span>
          </span>
        </a>
        <nav aria-label="Main">
          <a href="#/hosts" className={route === 'hosts' ? 'active' : ''} aria-current={route === 'hosts' ? 'page' : undefined}>
            Hosts
          </a>
          <a href="#/servers" className={route === 'servers' ? 'active' : ''} aria-current={route === 'servers' ? 'page' : undefined}>
            Servers
          </a>
        </nav>
      </header>
      <main className="board">
        {route === 'hosts' ? <HostsPage /> : <ServersPage />}
      </main>
    </>
  )
}

export default App
