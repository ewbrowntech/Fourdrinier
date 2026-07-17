import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type { HostRead, KeypairRead } from '../api'

type HostKind = 'docker' | 'kubernetes'

interface RegisterHostFormProps {
  keypairs: KeypairRead[]
  onCreated: (host: HostRead, generatedKeypair: KeypairRead | null) => void
  onCancel: () => void
}

function RegisterHostForm({ keypairs, onCreated, onCancel }: RegisterHostFormProps) {
  const [kind, setKind] = useState<HostKind>('docker')
  const [name, setName] = useState('')

  const [address, setAddress] = useState('')
  const [port, setPort] = useState('22')
  const [username, setUsername] = useState('')
  const [keypairChoice, setKeypairChoice] = useState<'generate' | string>('generate')
  const [newKeypairName, setNewKeypairName] = useState('')

  const [apiUrl, setApiUrl] = useState('')
  const [namespace, setNamespace] = useState('fourdrinier')
  const [token, setToken] = useState('')
  const [caCertPem, setCaCertPem] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      if (kind === 'docker') {
        let keypairId = keypairChoice
        let generated: KeypairRead | null = null
        if (keypairChoice === 'generate') {
          const keypairName = newKeypairName.trim() || `${name.trim()}-key`
          generated = await api.createKeypair(keypairName)
          keypairId = generated.id
          // If host creation fails below, the keypair already exists — point
          // the form at it so a retry doesn't create a duplicate.
          setKeypairChoice(generated.id)
        }
        const host = await api.createHost({
          type: 'docker',
          name: name.trim(),
          address: address.trim(),
          port: Number(port),
          username: username.trim(),
          keypair_id: keypairId,
        })
        onCreated(host, generated)
      } else {
        const host = await api.createHost({
          type: 'kubernetes',
          name: name.trim(),
          api_url: apiUrl.trim(),
          ca_cert_pem: caCertPem,
          token,
          namespace: namespace.trim(),
        })
        onCreated(host, null)
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
        <h2>Register a host</h2>
        <div className="segmented" role="radiogroup" aria-label="Host type">
          <button
            type="button"
            role="radio"
            aria-checked={kind === 'docker'}
            className={kind === 'docker' ? 'on' : ''}
            onClick={() => setKind('docker')}
          >
            Docker over SSH
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={kind === 'kubernetes'}
            className={kind === 'kubernetes' ? 'on' : ''}
            onClick={() => setKind('kubernetes')}
          >
            Kubernetes cluster
          </button>
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
            placeholder="basement-tower"
            autoFocus
          />
        </label>

        {kind === 'docker' ? (
          <>
            <label className="field">
              <span>Address</span>
              <input
                className="data"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
                placeholder="192.168.1.40"
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
                placeholder="minecraft"
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
                  placeholder={name.trim() ? `${name.trim()}-key` : 'my-host-key'}
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
                required
              />
            </label>
            <label className="field wide">
              <span>CA certificate (PEM)</span>
              <textarea
                className="data"
                value={caCertPem}
                onChange={(e) => setCaCertPem(e.target.value)}
                required
                rows={5}
                placeholder={'-----BEGIN CERTIFICATE-----\n…\n-----END CERTIFICATE-----'}
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
          {submitting ? 'Registering…' : 'Register host'}
        </button>
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default RegisterHostForm
