import { createFileRoute } from '@tanstack/react-router'
import HostDetailsPage from '../../pages/HostDetailsPage'

export const Route = createFileRoute('/hosts/$hostId')({
  component: HostDetailsRoute,
})

function HostDetailsRoute() {
  const { hostId } = Route.useParams()
  return <HostDetailsPage hostId={hostId} />
}
