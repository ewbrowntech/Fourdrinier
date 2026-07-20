import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api, SERVER_RUNTIMES } from '../api'
import type { ServerRead, ServerRuntime } from '../api'
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

type VersionsEntry =
  | { status: 'loading' }
  | { status: 'ready'; versions: string[] }
  | { status: 'error'; message: string }

const SINGLE_VERSION_TOOLTIP =
  'This runtime only supports one version of Minecraft.'

function CreateServerForm({ onCreated, onCancel }: CreateServerFormProps) {
  const runtimeListboxId = useId()
  const runtimeSelectRef = useRef<HTMLDivElement>(null)
  const versionsCacheRef = useRef<Partial<Record<ServerRuntime, VersionsEntry>>>({})
  const versionsInflightRef = useRef<Partial<Record<ServerRuntime, Promise<string[]>>>>({})

  const [name, setName] = useState('')
  const [runtime, setRuntime] = useState<ServerRuntime | ''>('')
  const [minecraftVersion, setMinecraftVersion] = useState('')
  const [versionsByRuntime, setVersionsByRuntime] = useState<
    Partial<Record<ServerRuntime, VersionsEntry>>
  >({})
  const [runtimeMenuOpen, setRuntimeMenuOpen] = useState(false)
  const [cpuCores, setCpuCores] = useState(String(DEFAULT_SERVER_RESOURCES.cpuCores))
  const [memoryGib, setMemoryGib] = useState(String(DEFAULT_SERVER_RESOURCES.memoryGib))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const minimumResources = runtime
    ? minimumResourcesForRuntime(runtime)
    : DEFAULT_SERVER_RESOURCES
  const selectedRuntimeLabel =
    SERVER_RUNTIMES.find((entry) => entry.id === runtime)?.label ?? 'Select a runtime'
  const versionsEntry = runtime ? versionsByRuntime[runtime] : undefined
  const versions = versionsEntry?.status === 'ready' ? versionsEntry.versions : []
  const singleVersionLocked = versionsEntry?.status === 'ready' && versions.length === 1
  const versionSelectDisabled =
    !runtime || versionsEntry?.status !== 'ready' || versions.length <= 1
  const versionPlaceholder =
    !runtime
      ? 'Select a runtime first'
      : versionsEntry?.status === 'loading'
        ? 'Loading versions…'
        : versionsEntry?.status === 'error'
          ? 'Could not load versions'
          : versions.length === 0
            ? 'No versions available'
            : 'Select a version'

  function rememberVersions(next: Partial<Record<ServerRuntime, VersionsEntry>>) {
    versionsCacheRef.current = next
    setVersionsByRuntime(next)
  }

  function prefetchVersions(target: ServerRuntime) {
    if (versionsInflightRef.current[target]) return
    const cached = versionsCacheRef.current[target]
    if (cached?.status === 'ready' || cached?.status === 'loading') return

    const loadingState: VersionsEntry = { status: 'loading' }
    rememberVersions({ ...versionsCacheRef.current, [target]: loadingState })

    const request = api
      .listRuntimeVersions(target)
      .then((loaded) => {
        const ready: VersionsEntry = { status: 'ready', versions: loaded }
        rememberVersions({ ...versionsCacheRef.current, [target]: ready })
        return loaded
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : 'Could not load Minecraft versions.'
        const failed: VersionsEntry = { status: 'error', message }
        rememberVersions({ ...versionsCacheRef.current, [target]: failed })
        return [] as string[]
      })
      .finally(() => {
        delete versionsInflightRef.current[target]
      })

    versionsInflightRef.current[target] = request
  }

  function applyReadyVersions(readyVersions: string[]) {
    if (readyVersions.length === 1) {
      setMinecraftVersion(readyVersions[0])
      return
    }
    setMinecraftVersion((current) => (readyVersions.includes(current) ? current : ''))
  }

  function selectRuntime(next: ServerRuntime) {
    setRuntime(next)
    setRuntimeMenuOpen(false)
    setError(null)

    const mins = minimumResourcesForRuntime(next)
    setCpuCores((current) => String(Math.max(Number(current) || 0, mins.cpuCores)))
    setMemoryGib((current) => String(Math.max(Number(current) || 0, mins.memoryGib)))

    prefetchVersions(next)

    const cached = versionsCacheRef.current[next]
    if (cached?.status === 'ready') {
      applyReadyVersions(cached.versions)
    } else {
      setMinecraftVersion('')
    }
  }

  useEffect(() => {
    if (!runtimeMenuOpen) return

    function handlePointerDown(event: MouseEvent) {
      if (!runtimeSelectRef.current?.contains(event.target as Node)) {
        setRuntimeMenuOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setRuntimeMenuOpen(false)
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [runtimeMenuOpen])

  useEffect(() => {
    if (!runtime || versionsEntry?.status !== 'ready') return
    applyReadyVersions(versionsEntry.versions)
  }, [runtime, versionsEntry])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!runtime || !minecraftVersion) {
      setError('Choose a runtime and Minecraft version before creating the server.')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const server = await api.createServer({
        name: name.trim(),
        runtime,
        minecraft_version: minecraftVersion,
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
          <h1>Create a server</h1>
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

        <div className="field">
          <span id={`${runtimeListboxId}-label`}>Runtime</span>
          <div className="field-select" ref={runtimeSelectRef}>
            <button
              type="button"
              className="field-select-trigger"
              aria-haspopup="listbox"
              aria-expanded={runtimeMenuOpen}
              aria-controls={runtimeListboxId}
              aria-labelledby={`${runtimeListboxId}-label`}
              onClick={() => setRuntimeMenuOpen((open) => !open)}
            >
              {selectedRuntimeLabel}
            </button>
            {runtimeMenuOpen && (
              <ul className="field-select-menu" role="listbox" id={runtimeListboxId}>
                {SERVER_RUNTIMES.map((entry) => (
                  <li key={entry.id} role="presentation">
                    <button
                      type="button"
                      role="option"
                      aria-selected={runtime === entry.id}
                      className={
                        runtime === entry.id
                          ? 'field-select-option on'
                          : 'field-select-option'
                      }
                      onMouseEnter={() => prefetchVersions(entry.id)}
                      onFocus={() => prefetchVersions(entry.id)}
                      onClick={() => selectRuntime(entry.id)}
                    >
                      {entry.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <label className="field">
          <span>Minecraft version</span>
          <span
            className="field-control-wrap"
            title={singleVersionLocked ? SINGLE_VERSION_TOOLTIP : undefined}
          >
            <select
              value={minecraftVersion}
              onChange={(event) => setMinecraftVersion(event.target.value)}
              disabled={versionSelectDisabled}
              required={Boolean(runtime)}
              aria-label={
                singleVersionLocked
                  ? `Minecraft version (${SINGLE_VERSION_TOOLTIP})`
                  : undefined
              }
            >
              {!singleVersionLocked && <option value="">{versionPlaceholder}</option>}
              {versions.map((version) => (
                <option key={version} value={version}>
                  {version}
                </option>
              ))}
            </select>
          </span>
          {runtime && versionsEntry?.status === 'error' && (
            <span className="field-hint fault" role="alert">
              {versionsEntry.message}
            </span>
          )}
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

      {runtime && (
        <p className="resource-note">
          {selectedRuntimeLabel} requires at least {minimumResources.cpuCores} cores and{' '}
          {minimumResources.memoryGib} GiB of memory.
        </p>
      )}

      <dl className="server-fixed-spec server-fixed-spec-single">
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
        <button
          type="submit"
          className="btn primary"
          disabled={submitting || !runtime || !minecraftVersion}
        >
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
