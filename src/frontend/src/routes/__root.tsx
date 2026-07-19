import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="appbar">
        <Link className="brand" to="/hosts">
          <svg className="brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="var(--brand-tint)" stroke="var(--brand)" strokeWidth="1.5" />
            <path d="M5 9h14M5 12h14M5 15h14" stroke="var(--brand)" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M9 5v14M12 5v14M15 5v14" stroke="var(--brand)" strokeWidth="1.5" strokeLinecap="round" opacity="0.35" />
          </svg>
          <span className="brand-text">
            <span className="brand-name">Fourdrinier</span>
            <span className="brand-sub">Server mill</span>
          </span>
        </Link>
        <nav aria-label="Main">
          <Link
            to="/hosts"
            activeOptions={{ includeSearch: false }}
            activeProps={{ className: 'active', 'aria-current': 'page' }}
          >
            Hosts
          </Link>
          <Link
            to="/servers"
            activeProps={{ className: 'active', 'aria-current': 'page' }}
          >
            Servers
          </Link>
        </nav>
      </header>
      <main id="main-content" className="board" tabIndex={-1}>
        <Outlet />
      </main>
      <TanStackRouterDevtools position="bottom-right" />
    </>
  )
}
