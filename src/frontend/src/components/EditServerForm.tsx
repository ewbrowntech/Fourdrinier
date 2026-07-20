import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, runtimeLabel } from '../api'
import type { ServerRead, ServerUpdate } from '../api'
import {
  bytesToGibibytes,
  coresToMillicores,
  gibibytesToBytes,
  millicoresToCores,
  minimumResourcesForRuntime,
} from '../serverResources'

interface EditServerFormProps {
  server: ServerRead
  onUpdated: (server: ServerRead) => void
  onCancel: () => void
}

function EditServerForm({ server, onUpdated, onCancel }: EditServerFormProps) {
  const minimumResources = minimumResourcesForRuntime(server.runtime)
  const [name, setName] = useState(server.name)
  const [cpuCores, setCpuCores] = useState(String(millicoresToCores(server.cpu_millicores)))
  const [memoryGib, setMemoryGib] = useState(String(bytesToGibibytes(server.memory_bytes)))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    const patch: ServerUpdate = {}
    const trimmedName = name.trim()
    const cpuMillicores = coresToMillicores(Number(cpuCores))
    const memoryBytes = gibibytesToBytes(Number(memoryGib))

    if (trimmedName !== server.name) patch.name = trimmedName
    if (cpuMillicores !== server.cpu_millicores) patch.cpu_millicores = cpuMillicores
    if (memoryBytes !== server.memory_bytes) patch.memory_bytes = memoryBytes

    try {
      onUpdated(await api.updateServer(server.id, patch))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the server changes.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <div className="panel-head">
        <h2>Edit {server.name}</h2>
      </div>

      <div className="field-grid">
        <label className="field wide">
          <span>Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={255}
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
        {runtimeLabel(server.runtime)} requires at least {minimumResources.cpuCores} cores and{' '}
        {minimumResources.memoryGib} GiB of memory. Changing either allocation creates a new
        specification generation for the next deployment.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="form-actions">
        <button type="submit" className="btn primary" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default EditServerForm
