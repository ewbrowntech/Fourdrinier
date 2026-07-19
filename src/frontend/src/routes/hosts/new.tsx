import { createFileRoute } from '@tanstack/react-router'
import NewHostPage from '../../pages/NewHostPage'

export const Route = createFileRoute('/hosts/new')({
  component: NewHostPage,
})
