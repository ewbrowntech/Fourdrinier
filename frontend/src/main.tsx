-import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './index.css'

// const queryClient = new QueryClient({
//   defaultOptions: {
//     queries: {
//       refetchOnWindowFocus: false,
//       staleTime: 30_000,
//       retry: 1,
//     },
//     mutations: {
//       retry: 1,
//     },
//   },
// })

// const THEME_STORAGE_KEY = 'fourdrinier-theme'

// function ThemeProvider({ children }: { children: ReactNode }) {
//   useEffect(() => {
//     const root = document.documentElement
//     const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

//     const applyTheme = (value: string) => {
//       root.classList.toggle('dark', value === 'dark')
//     }

//     const stored = localStorage.getItem(THEME_STORAGE_KEY)
//     applyTheme(stored ?? (mediaQuery.matches ? 'dark' : 'light'))

//     const handleMediaChange = (event: MediaQueryListEvent) => {
//       if (localStorage.getItem(THEME_STORAGE_KEY)) return
//       applyTheme(event.matches ? 'dark' : 'light')
//     }

//     mediaQuery.addEventListener('change', handleMediaChange)
//     return () => mediaQuery.removeEventListener('change', handleMediaChange)
//   }, [])

//   return <>{children}</>
// }

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Root container missing in index.html')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
