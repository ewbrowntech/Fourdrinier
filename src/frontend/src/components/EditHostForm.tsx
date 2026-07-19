import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type {
  DockerHostRead,
  DockerHostUpdate,
  HostRead,
  KeypairRead,
  KubernetesHostRead,
  KubernetesHostUpdate,
} from '../api'

interface EditHostFormProps {
  host: HostRead
  keypairs: KeypairRead[]
  onUpdated: (host: HostRead, generatedKeypair: KeypairRead | null) => void
  onCancel: () => void
}

function EditHostForm({ host, keypairs, onUpdated, onCancel }: EditHostFormProps) {
  const docker = host.type === 'docker' ? (host as DockerHostRead) : null
  const kube = host.type === 'kubernetes' ? (host as KubernetesHostRead) : null

  const [name, setName] = useState(host.name)
  const [enabled, setEnabled] = useState(host.enabled)

  const [address, setAddress] = useState(docker?.address ?? '')
  const [port, setPort] = useState(String(docker?.port ?? 22))
  const [username, setUsername] = useState(docker?.username ?? '')
  const [keypairChoice, setKeypairChoice] = useState<'generate' | string>(docker?.keypair_id ?? '')
  const [newKeypairName, setNewKeypairName] = useState('')

  const [apiUrl, setApiUrl] = useState(kube?.api_url ?? '')
  const [namespace, setNamespace] = useState(kube?.namespace ?? '')
  const [token, setToken] = useState('')
  const [caCertPem, setCaCertPem] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      if (host.type === 'docker' && docker) {
        const patch: DockerHostUpdate = { type: 'docker' }
        let generated: KeypairRead | null = null

        const trimmedName = name.trim()
        if (trimmedName !== docker.name) patch.name = trimmedName
        if (enabled !== docker.enabled) patch.enabled = enabled
        if (address.trim() !== docker.address) patch.address = address.trim()
        if (Number(port) !== docker.port) patch.port = Number(port)
        if (username.trim() !== docker.username) patch.username = username.trim()

        if (keypairChoice === 'generate') {
          const keypairName = newKeypairName.trim() || `${trimmedName || docker.name}-key`
          generated = await api.createKeypair(keypairName)
          patch.keypair_id = generated.id
          // If the update fails below, the keypair already exists — point the
          // form at it so a retry doesn't create a duplicate.
          setKeypairChoice(generated.id)
        } else if (keypairChoice !== docker.keypair_id) {
          patch.keypair_id = keypairChoice
        }

        const updated = await api.updateHost(host.id, patch)
        onUpdated(updated, generated)
      } else if (host.type === 'kubernetes' && kube) {
        const patch: KubernetesHostUpdate = { type: 'kubernetes' }

        const trimmedName = name.trim()
        if (trimmedName !== kube.name) patch.name = trimmedName
        if (enabled !== kube.enabled) patch.enabled = enabled
        if (apiUrl.trim() !== kube.api_url) patch.api_url = apiUrl.trim()
        if (namespace.trim() !== kube.namespace) patch.namespace = namespace.trim()
        // Credentials are write-only: send only when the operator supplies a
        // replacement, otherwise leave the stored value untouched.
        if (token) patch.token = token
        if (caCertPem.trim()) patch.ca_cert_pem = caCertPem

        const updated = await api.updateHost(host.id, patch)
        onUpdated(updated, null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <div className="panel-head">
        <h2>Edit {host.name}</h2>
        <div className="segmented" role="radiogroup" aria-label="Enabled">
          <label className={enabled ? 'on' : undefined}>
            <input
              type="radio"
              name="host-enabled"
              value="enabled"
              checked={enabled}
              onChange={() => setEnabled(true)}
            />
            Enabled
          </label>
          <label className={!enabled ? 'on' : undefined}>
            <input
              type="radio"
              name="host-enabled"
              value="disabled"
              checked={!enabled}
              onChange={() => setEnabled(false)}
            />
            Disabled
          </label>
        </div>
      </div>

      <div className="field-grid">
        <label className="field">
          <span>Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={255}
            autoFocus
          />
        </label>

        {host.type === 'docker' ? (
          <>
            <label className="field">
              <span>Address</span>
              <input
                className="data"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </label>
            <label className="field narrow">
              <span>SSH port</span>
              <input
                className="data"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                required
                inputMode="numeric"
                pattern="[0-9]+"
              />
            </label>
            <label className="field">
              <span>Username</span>
              <input
                className="data"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>SSH keypair</span>
              <select value={keypairChoice} onChange={(e) => setKeypairChoice(e.target.value)}>
                <option value="generate">Generate a new keypair</option>
                {keypairs.map((kp) => (
                  <option key={kp.id} value={kp.id}>
                    {kp.name} ({kp.algorithm})
                  </option>
                ))}
              </select>
            </label>
            {keypairChoice === 'generate' && (
              <label className="field">
                <span>Keypair name</span>
                <input
                  value={newKeypairName}
                  onChange={(e) => setNewKeypairName(e.target.value)}
                  maxLength={255}
                  placeholder={`${name.trim() || host.name}-key`}
                />
              </label>
            )}
          </>
        ) : (
          <>
            <label className="field wide">
              <span>API URL</span>
              <input
                className="data"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                required
                placeholder="https://cluster.local:6443"
              />
            </label>
            <label className="field">
              <span>Namespace</span>
              <input
                className="data"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                required
                maxLength={63}
              />
            </label>
            <label className="field">
              <span>Service account token</span>
              <input
                className="data"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Leave blank to keep current"
              />
            </label>
            <label className="field wide">
              <span>CA certificate (PEM)</span>
              <textarea
                className="data"
                value={caCertPem}
                onChange={(e) => setCaCertPem(e.target.value)}
                rows={5}
                placeholder="Leave blank to keep current"
                spellCheck={false}
              />
            </label>
          </>
        )}
      </div>

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

export default EditHostForm
