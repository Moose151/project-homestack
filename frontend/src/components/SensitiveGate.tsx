import { useState } from 'react'
import { api } from '../api/client'
import { Button } from './Button'
import { Card } from './Card'
import { Field, Input } from './Field'

/**
 * The one locked state for a sensitive node.
 *
 * Money had its own unlock screen and Homestead's protected costs had none, so a locked node
 * looked like whatever the page happened to implement. The API now refuses with
 * `code: "reauth_required"` and the node key, so any surface can show this instead of
 * string-matching an error sentence (Milestone 4).
 */
export function SensitiveGate({
  nodeName,
  onUnlock,
  hint,
}: {
  nodeName: string
  onUnlock: () => void
  hint?: string
}) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!password) return
    setSaving(true); setError('')
    try {
      await api.reauth(password)
      setPassword('')
      onUnlock()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'That password was not accepted.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg pt-8">
      <Card contentClassName="p-5">
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-xl font-bold text-ink">Unlock {nodeName}</h2>
            <p className="mt-1 text-sm text-muted">
              {hint ?? 'Enter your account password to open this area.'}
            </p>
          </div>
          {error && (
            <div role="alert" className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}
          <Field label="Password">
            <Input
              type="password"
              autoFocus
              value={password}
              onChange={event => setPassword(event.target.value)}
              onKeyDown={event => { if (event.key === 'Enter') void submit() }}
            />
          </Field>
          <Button onClick={submit} loading={saving} disabled={!password}>Unlock</Button>
          <p className="text-xs text-muted">
            Unlocking lasts a few minutes, and far less on the kiosk — a shared screen should not
            stay open behind you.
          </p>
        </div>
      </Card>
    </div>
  )
}

/** True when a failed request was refused because the node is locked, not for another reason. */
export function isLockedError(error: unknown): boolean {
  return Boolean(
    error
    && typeof error === 'object'
    && (error as { code?: string }).code === 'reauth_required',
  )
}
