import { createFileRoute } from '@tanstack/react-router'
import HostsPage from '../../pages/HostsPage'

export const Route = createFileRoute('/hosts/')({
  component: HostsPage,
})
