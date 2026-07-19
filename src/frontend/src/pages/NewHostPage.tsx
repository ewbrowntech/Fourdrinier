import { useEffect, useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { api } from '../api'
import type { HostRead, KeypairRead } from '../api'
import RegisterHostForm from '../components/RegisterHostForm'
import { setPendingHost } from '../pendingHost'

function NewHostPage() {
  const navigate = useNavigate()
  const [keypairs, setKeypairs] = useState<KeypairRead[]>([])

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const loaded = await api.listKeypairs()
        if (active) setKeypairs(loaded)
      } catch {
        if (active) setKeypairs([])
      }
    })()
    return () => {
      active = false
    }
  }, [])

  function handleCreated(host: HostRead, generated: KeypairRead | null) {
    // Hand the new host to the list, which runs the connectivity ping and shows
    // the generated-key notice once it mounts.
    setPendingHost({ host, generatedKeypair: generated })
    void navigate({ to: '/hosts' })
  }

  return (
    <>
      <Link className="back-link" to="/hosts">
        ← Hosts
      </Link>
      <RegisterHostForm
        keypairs={keypairs}
        onCreated={handleCreated}
        onCancel={() => {
          void navigate({ to: '/hosts' })
        }}
      />
    </>
  )
}

export default NewHostPage
