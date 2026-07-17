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
      <header className="appbar">
        <a className="brand" href="#/hosts">
          <svg className="brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="var(--brand-tint)" stroke="var(--brand)" strokeWidth="1.5" />
            <path d="M5 9h14M5 12h14M5 15h14" stroke="var(--brand)" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M9 5v14M12 5v14M15 5v14" stroke="var(--brand)" strokeWidth="1.5" strokeLinecap="round" opacity="0.35" />
          </svg>
          <span className="brand-text">
            <span className="brand-name">Fourdrinier</span>
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
