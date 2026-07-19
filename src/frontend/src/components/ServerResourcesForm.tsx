import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type { ServerRead } from '../api'
import {
  bytesToGibibytes,
  coresToMillicores,
  gibibytesToBytes,
  millicoresToCores,
  minimumResourcesForRuntime,
} from '../serverResources'

interface ServerResourcesFormProps {
  server: ServerRead
  onUpdated: (server: ServerRead) => void
}

function ServerResourcesForm({ server, onUpdated }: ServerResourcesFormProps) {
  const minimumResources = minimumResourcesForRuntime(server.runtime)
  const [cpuCores, setCpuCores] = useState(String(millicoresToCores(server.cpu_millicores)))
  const [memoryGib, setMemoryGib] = useState(String(bytesToGibibytes(server.memory_bytes)))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setCpuCores(String(millicoresToCores(server.cpu_millicores)))
    setMemoryGib(String(bytesToGibibytes(server.memory_bytes)))
  }, [server.cpu_millicores, server.memory_bytes])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateServer(server.id, {
        cpu_millicores: coresToMillicores(Number(cpuCores)),
        memory_bytes: gibibytesToBytes(Number(memoryGib)),
      })
      onUpdated(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the resource allocation.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel resource-panel" onSubmit={handleSubmit}>
      <div className="panel-head">
        <div>
          <p className="panel-kicker">Compute envelope</p>
          <h2>Resource allocation</h2>
        </div>
        <span className="resource-generation">Generation {server.spec_generation}</span>
      </div>

      <div className="field-grid resource-fields">
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
        {minimumResources.memoryGib} GiB of memory. Changing either value creates a new
        specification generation for the next deployment.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="form-actions">
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save allocation'}
        </button>
      </div>
    </form>
  )
}

export default ServerResourcesForm
