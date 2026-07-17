import { createFileRoute } from '@tanstack/react-router'
import ServersPage from '../pages/ServersPage'

export const Route = createFileRoute('/servers')({
  component: ServersPage,
})
