import { createFileRoute } from '@tanstack/react-router'
import ServerDetailsPage from '../../pages/ServerDetailsPage'

export const Route = createFileRoute('/servers/$serverId')({
  component: ServerDetailsRoute,
})

function ServerDetailsRoute() {
  const { serverId } = Route.useParams()
  return <ServerDetailsPage serverId={serverId} />
}
