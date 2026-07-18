import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type { ServerRead } from '../api'

interface CreateServerFormProps {
  onCreated: (server: ServerRead) => void
  onCancel: () => void
}

function CreateServerForm({ onCreated, onCancel }: CreateServerFormProps) {
  const [name, setName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const server = await api.createServer({ name: name.trim(), runtime: 'pumpkin' })
      onCreated(server)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the server.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="panel server-create-panel" onSubmit={handleSubmit}>
      <div className="panel-head">
        <div>
          <p className="panel-kicker">Saved configuration</p>
          <h1>Create a Pumpkin server</h1>
        </div>
        <span className="experimental-tag">Experimental</span>
      </div>

      <div className="field-grid">
        <label className="field wide">
          <span>Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={255}
            placeholder="weekend-world"
            autoFocus
          />
        </label>
      </div>

      <dl className="server-fixed-spec">
        <div>
          <dt>Runtime</dt>
          <dd>Pumpkin</dd>
        </div>
        <div>
          <dt>Minecraft version</dt>
          <dd>Assigned from Pumpkin</dd>
        </div>
        <div>
          <dt>Initial state</dt>
          <dd>Stopped</dd>
        </div>
      </dl>

      <p className="scope-note">
        This saves a server plan only. It will not choose a host, download an image, or start a
        Minecraft process.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="form-actions">
        <button type="submit" className="btn primary" disabled={submitting}>
          {submitting ? 'Creating…' : 'Create server'}
        </button>
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default CreateServerForm
