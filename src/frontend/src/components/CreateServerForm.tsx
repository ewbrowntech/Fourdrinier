import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type { ServerRead } from '../api'
import {
  coresToMillicores,
  DEFAULT_SERVER_RESOURCES,
  gibibytesToBytes,
  minimumResourcesForRuntime,
} from '../serverResources'

interface CreateServerFormProps {
  onCreated: (server: ServerRead) => void
  onCancel: () => void
}

function CreateServerForm({ onCreated, onCancel }: CreateServerFormProps) {
  const runtime = 'pumpkin' as const
  const minimumResources = minimumResourcesForRuntime(runtime)
  const [name, setName] = useState('')
  const [cpuCores, setCpuCores] = useState(
    String(Math.max(DEFAULT_SERVER_RESOURCES.cpuCores, minimumResources.cpuCores)),
  )
  const [memoryGib, setMemoryGib] = useState(
    String(Math.max(DEFAULT_SERVER_RESOURCES.memoryGib, minimumResources.memoryGib)),
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const server = await api.createServer({
        name: name.trim(),
        runtime,
        cpu_millicores: coresToMillicores(Number(cpuCores)),
        memory_bytes: gibibytesToBytes(Number(memoryGib)),
      })
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
        <label className="field">
          <span>CPU allocation</span>
          <span className="input-with-unit">
            <input
              className="data"
              type="number"
              min={minimumResources.cpuCores}
              step="0.001"
              value={cpuCores}
              onChange={(event) => setCpuCores(event.target.value)}
              required
            />
            <span>cores</span>
          </span>
        </label>
        <label className="field">
          <span>Memory allocation</span>
          <span className="input-with-unit">
            <input
              className="data"
              type="number"
              min={minimumResources.memoryGib}
              step="0.001"
              value={memoryGib}
              onChange={(event) => setMemoryGib(event.target.value)}
              required
            />
            <span>GiB</span>
          </span>
        </label>
      </div>

      <p className="resource-note">
        Pumpkin requires at least {minimumResources.cpuCores} cores and{' '}
        {minimumResources.memoryGib} GiB of memory.
      </p>

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
