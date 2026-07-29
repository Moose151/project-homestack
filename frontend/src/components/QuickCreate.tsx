import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Button } from './Button'
import { Input } from './Field'
import { Modal } from './Modal'

const ACTIONS = [
  { key: 'event', label: 'Event', icon: '📅', route: '/calendar?new=event', node: null },
  { key: 'task', label: 'Meridian task', icon: '⭐', route: '/meridian?tab=tasks&new=task', node: 'meridian' },
  { key: 'bill', label: 'Bill', icon: '💸', route: '/solace?tab=bills&new=bill', node: 'solace' },
  { key: 'maintenance', label: 'Maintenance', icon: '🛠️', route: '/homestead?tab=maintenance&new=maintenance', node: 'homestead' },
  { key: 'book', label: 'Book', icon: '📚', route: '/books?new=book', node: 'books' },
] as const

export function QuickCreate({
  open,
  onClose,
  enabledKeys,
}: {
  open: boolean
  onClose: () => void
  enabledKeys: Set<string>
}) {
  const navigate = useNavigate()
  const [kind, setKind] = useState<'reminder' | 'note'>('reminder')
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
      if (kind === 'reminder') await api.createReminder({ title })
      else await api.createNote({ title })
      setText('')
      setMessage(kind === 'reminder' ? 'Reminder added' : 'Note saved')
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

  return (
    <Modal title="Create something" onClose={onClose} size="md">
      <div className="space-y-5">
        {enabledKeys.has('atlas') && (
          <form onSubmit={create} className="space-y-3 rounded-2xl bg-sunken p-3">
            <div className="flex rounded-xl bg-surface p-1">
              {(['reminder', 'note'] as const).map(option => (
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
              <Input value={text} onChange={event => setText(event.target.value)} placeholder={kind === 'reminder' ? 'Remind me to…' : 'Note title…'} />
              <Button type="submit" loading={busy} disabled={!text.trim()}>Add</Button>
            </div>
            {message && <p className="text-xs text-muted-strong">{message}</p>}
          </form>
        )}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {ACTIONS.filter(action => !action.node || enabledKeys.has(action.node)).map(action => (
            <button
              key={action.key}
              onClick={() => go(action.route)}
              className="flex min-h-[92px] flex-col items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-3 text-sm font-semibold text-ink transition-colors hover:bg-sunken"
            >
              <span className="text-2xl">{action.icon}</span>
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </Modal>
  )
}
