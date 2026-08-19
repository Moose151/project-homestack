import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Button } from './Button'
import { Input } from './Field'
import { Modal } from './Modal'

const ACTIONS = [
  { key: 'event', label: 'Calendar event', hint: 'Put something on the family calendar', icon: '📅', route: '/calendar?new=event', node: null, contexts: ['calendar'] },
  { key: 'home-plan', label: 'Home plan', hint: 'Plan a room purchase or project', icon: '🏠', route: '/homestead?tab=rooms', node: 'homestead', contexts: ['homestead'] },
  { key: 'maintenance', label: 'Maintenance', hint: 'Remember a job around the house', icon: '🛠️', route: '/homestead?tab=maintenance&new=maintenance', node: 'homestead', contexts: ['homestead'] },
  { key: 'book', label: 'Book', hint: 'Add something to read', icon: '📚', route: '/books?new=book', node: 'books', contexts: ['books'] },
  { key: 'task', label: 'Points task', hint: 'Create a family job or reward task', icon: '⭐', route: '/meridian?tab=tasks&new=task', node: 'meridian', contexts: ['meridian'] },
  { key: 'bill', label: 'Household bill', hint: 'Add a payment to the money plan', icon: '💸', route: '/solace?tab=bills&new=bill', node: 'solace', contexts: ['solace'] },
] as const

export function QuickCreate({
  open,
  onClose,
  enabledKeys,
  contextKey,
}: {
  open: boolean
  onClose: () => void
  enabledKeys: Set<string>
  contextKey?: string
}) {
  const navigate = useNavigate()
  // 'reminder' is not one of these on purpose: a reminder is a property of a to-do since
  // v0.40 (D19 §E), not a second kind of record that also lands on the calendar.
  const [kind, setKind] = useState<'to-do' | 'note'>('to-do')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  if (!open) return null

  const create = async (event: React.FormEvent) => {
    event.preventDefault()
    const title = text.trim()
    if (!title) return
    setBusy(true)
    setMessage('')
    try {
      if (kind === 'to-do') await api.quickCreateTodo({ title })
      else await api.createNote({ title })
      setText('')
      setMessage(kind === 'to-do' ? 'To-do added' : 'Note saved')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  const go = (route: string) => {
    navigate(route)
    onClose()
  }

  const visibleActions = ACTIONS.filter(action => !action.node || enabledKeys.has(action.node))
  const contextualActions = visibleActions.filter(action => action.contexts.some(context => context === contextKey))
  const globalActions = visibleActions.filter(action => !contextualActions.includes(action))

  const actionButton = (action: (typeof ACTIONS)[number]) => (
    <button
      key={action.key}
      onClick={() => go(action.route)}
      data-contextual={contextualActions.includes(action) || undefined}
      className="flex min-h-[112px] flex-col items-center justify-center gap-1 rounded-2xl border border-line bg-surface p-3 text-center transition-all hover:-translate-y-0.5 hover:bg-sunken active:scale-[0.98] motion-reduce:transform-none motion-reduce:transition-none"
    >
      <span className="text-2xl">{action.icon}</span>
      <span className="text-sm font-semibold text-ink">{action.label}</span>
      <span className="text-[11px] leading-snug text-muted">{action.hint}</span>
    </button>
  )

  return (
    <Modal title="Add something" onClose={onClose} size="md">
      <div className="space-y-5">
        {enabledKeys.has('atlas') && (
          <form onSubmit={create} className="space-y-3 rounded-2xl bg-sunken p-3">
            <div className="flex rounded-xl bg-surface p-1">
              {(['to-do', 'note'] as const).map(option => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setKind(option)}
                  className={`flex-1 rounded-lg px-3 py-2 text-xs font-semibold capitalize ${kind === option ? 'bg-raised text-ink shadow-soft' : 'text-muted'}`}
                >
                  {option}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Input value={text} onChange={event => setText(event.target.value)} placeholder={kind === 'to-do' ? 'Remind me to…' : 'Note title…'} />
              <Button type="submit" loading={busy} disabled={!text.trim()}>Add</Button>
            </div>
            {message && <p className="text-xs text-muted-strong">{message}</p>}
          </form>
        )}
        {contextualActions.length > 0 && (
          <section aria-labelledby="quick-create-suggested">
            <h3 id="quick-create-suggested" className="mb-2 text-xs font-extrabold uppercase tracking-[0.12em] text-muted">Suggested here</h3>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{contextualActions.map(actionButton)}</div>
          </section>
        )}
        {globalActions.length > 0 && (
          <section aria-labelledby="quick-create-everywhere">
            <h3 id="quick-create-everywhere" className="mb-2 text-xs font-extrabold uppercase tracking-[0.12em] text-muted">
              {contextualActions.length > 0 ? 'More ways to add' : 'Add anywhere'}
            </h3>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{globalActions.map(actionButton)}</div>
          </section>
        )}
      </div>
    </Modal>
  )
}
