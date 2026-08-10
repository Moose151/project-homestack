import { useEffect, useState, type ReactNode } from 'react'

import { Button } from './Button'
import { Field, fieldClass } from './Field'
import { Modal } from './Modal'

/**
 * In-app replacements for `window.confirm` and `window.prompt`.
 *
 * The native dialogs are system alerts: on a phone they drop out of the browser chrome, state
 * the origin ("localhost:5173 says"), ignore the household's theme, and offer only OK/Cancel
 * with no danger tone. Every destructive action and every approval note in the app therefore
 * ended in something that looked like a browser error rather than part of HomeStack. The
 * native prompt is worse still — a bare single-line box with no label, no keyboard hint and no
 * validation.
 *
 * Deliberately module-level functions rather than hooks, so a call site changes from
 * `if (confirm('…'))` to `if (await confirmDialog({ … }))` without threading a provider through
 * every nested component that happens to own a delete button.
 */
export interface ConfirmOptions {
  /** The question, phrased as the thing that is about to happen. */
  title: string
  /** Optional detail: what is lost, what stays, what cannot be undone. */
  message?: ReactNode
  /** The verb for the action itself — "Delete pet", not "OK". */
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'danger' | 'primary'
}

export interface PromptOptions {
  title: string
  message?: ReactNode
  /** Field label. Defaults to the title, so the box is never unlabelled. */
  label?: string
  placeholder?: string
  defaultValue?: string
  confirmLabel?: string
  cancelLabel?: string
  /** `decimal` and `numeric` open the number keypad on a phone instead of the full keyboard. */
  inputMode?: 'text' | 'numeric' | 'decimal'
  /** Block the confirm button until something is entered. */
  required?: boolean
}

type Pending =
  | ({ kind: 'confirm'; resolve: (value: boolean) => void } & ConfirmOptions)
  | ({ kind: 'prompt'; resolve: (value: string | null) => void } & PromptOptions)

let present: ((request: Pending) => void) | null = null

export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  if (!present) {
    // No host mounted (kiosk, tests). Degrading to the native dialog keeps the guard rail.
    return Promise.resolve(window.confirm(nativeText(options.title, options.message)))
  }
  return new Promise<boolean>(resolve => present?.({ kind: 'confirm', ...options, resolve }))
}

export function promptDialog(options: PromptOptions): Promise<string | null> {
  if (!present) {
    return Promise.resolve(window.prompt(nativeText(options.title, options.message), options.defaultValue ?? ''))
  }
  return new Promise<string | null>(resolve => present?.({ kind: 'prompt', ...options, resolve }))
}

function nativeText(title: string, message?: ReactNode) {
  return [title, typeof message === 'string' ? message : ''].filter(Boolean).join('\n\n')
}

/** Mount once, inside the shell. Renders whichever dialog is currently pending. */
export function DialogHost() {
  const [request, setRequest] = useState<Pending | null>(null)
  const [value, setValue] = useState('')

  useEffect(() => {
    present = setRequest
    return () => { present = null }
  }, [])

  useEffect(() => {
    if (request?.kind === 'prompt') setValue(request.defaultValue ?? '')
  }, [request])

  if (!request) return null

  const finish = (confirmed: boolean) => {
    if (request.kind === 'confirm') request.resolve(confirmed)
    else request.resolve(confirmed ? value : null)
    setRequest(null)
  }

  const isPrompt = request.kind === 'prompt'
  const blocked = isPrompt && request.required === true && !value.trim()

  return (
    <Modal title={request.title} size="sm" onClose={() => finish(false)}>
      {request.message && <div className="text-sm leading-relaxed text-muted-strong">{request.message}</div>}
      {isPrompt && (
        <form
          className={request.message ? 'mt-4' : ''}
          onSubmit={event => { event.preventDefault(); if (!blocked) finish(true) }}
        >
          <Field label={request.label || request.title}>
            <input
              data-autofocus
              className={fieldClass}
              value={value}
              inputMode={request.inputMode === 'text' ? undefined : request.inputMode}
              placeholder={request.placeholder}
              onChange={event => setValue(event.target.value)}
            />
          </Field>
        </form>
      )}
      {/* Stacked and full-width on phones: side-by-side buttons at the bottom of a sheet put
          the destructive verb under the thumb that was reaching for Cancel. */}
      <div className={`flex flex-col-reverse gap-2 sm:flex-row sm:justify-end ${request.message || isPrompt ? 'mt-5' : ''}`}>
        <Button variant="ghost" className="w-full sm:w-auto" onClick={() => finish(false)}>
          {request.cancelLabel || 'Cancel'}
        </Button>
        <Button
          variant={isPrompt || request.tone === 'primary' ? 'primary' : 'danger'}
          className="w-full sm:w-auto"
          disabled={blocked}
          onClick={() => finish(true)}
        >
          {request.confirmLabel || (isPrompt ? 'Save' : 'Confirm')}
        </Button>
      </div>
    </Modal>
  )
}
