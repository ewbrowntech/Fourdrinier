import { Link, useNavigate } from '@tanstack/react-router'
import type { ServerRead } from '../api'
import CreateServerForm from '../components/CreateServerForm'

function NewServerPage() {
  const navigate = useNavigate()

  function handleCreated(server: ServerRead) {
    void navigate({ to: '/servers/$serverId', params: { serverId: server.id } })
  }

  return (
    <>
      <Link className="back-link" to="/servers">
        ← Servers
      </Link>
      <CreateServerForm
        onCreated={handleCreated}
        onCancel={() => void navigate({ to: '/servers' })}
      />
    </>
  )
}

export default NewServerPage
