import { createFileRoute } from '@tanstack/react-router'
import NewServerPage from '../../pages/NewServerPage'

export const Route = createFileRoute('/servers/new')({
  component: NewServerPage,
})
