import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { AdminUser, Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Avatar } from '../../../components/Avatar'
import { useAuth } from '../../auth/AuthContext'

const ROLES = ['admin', 'manager', 'user', 'guest'] as const
const ROLE_BADGE: Record<string, string> = {
  admin: 'bg-danger-soft text-danger', manager: 'bg-warning-soft text-warning',
  user: 'bg-primary-soft text-primary', guest: 'bg-sunken text-muted-strong',
}
const input = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

const AVATAR_EMOJIS = [
  '😀', '😎', '🦊', '🐱', '🐶', '🐰', '🐻', '🐼', '🦁', '🐸', '🦄', '🐧',
  '🦉', '🐢', '🐝', '🌟', '🌈', '🍀', '🍎', '🍕', '⚽', '🎮', '🎨', '🎸',
  '🚀', '🏰', '👑', '❤️',
]

function EmojiPicker({ value, colour, onChange }: { value: string; colour: string; onChange: (e: string) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Avatar name="?" colour={colour} avatar={value} size="lg" />
        <span className="text-sm text-muted">Account picture (emoji)</span>
        {value && (
          <button type="button" onClick={() => onChange('')} className="text-xs text-muted hover:text-danger">
            clear
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {AVATAR_EMOJIS.map(e => (
          <button
            key={e}
            type="button"
            onClick={() => onChange(e)}
            className={`w-9 h-9 rounded-lg text-lg flex items-center justify-center transition-colors ${
              value === e ? 'bg-primary-soft ring-2 ring-primary' : 'bg-sunken hover:bg-line'
            }`}
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  )
}

export function UsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const reload = async () => {
    const [u, p] = await Promise.all([api.getUsers().catch(() => []), api.getPeople().catch(() => [])])
    setUsers(u); setPeople(p); setLoading(false)
  }
  useEffect(() => { reload() }, [])

  if (user?.role !== 'admin') {
    return <p className="text-sm text-muted">Only admins can manage users.</p>
  }
  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  const unlinkedPeople = people.filter(p => p.linked_user_id == null)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">Users</h1>
        <Button size="sm" onClick={() => { setShowForm(s => !s); setErr(null) }}>
          {showForm ? 'Close' : 'New user'}
        </Button>
      </div>

      {err && <p className="text-sm text-danger">{err}</p>}

      {showForm && (
        <UserForm people={unlinkedPeople} onError={setErr}
          onSaved={() => { setShowForm(false); reload() }} />
      )}

      <div className="flex flex-col gap-2">
        {users.map(u => (
          <Card key={u.id} className={u.is_active ? '' : 'opacity-60'}>
            <div className="flex items-center gap-3 flex-wrap">
              <Avatar name={u.display_name} colour={u.colour} avatar={u.avatar} size="md" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-ink">{u.display_name}</span>
                  <span className="text-xs text-muted">@{u.username}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${ROLE_BADGE[u.role]}`}>{u.role}</span>
                  {u.is_child_account && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">child</span>}
                  {!u.is_active && <span className="text-xs px-2 py-0.5 rounded-full bg-danger-soft text-danger">inactive</span>}
                </div>
                {u.linked_person_name && <p className="text-xs text-muted mt-0.5">Person: {u.linked_person_name}</p>}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setEditing(editing === u.id ? null : u.id)}>
                  {editing === u.id ? 'Close' : 'Edit'}
                </Button>
                {u.is_active && u.id !== user.id && (
                  <Button size="sm" variant="ghost"
                    onClick={() => { if (confirm(`Deactivate ${u.display_name}?`)) api.deactivateUser(u.id).then(reload) }}>
                    Deactivate
                  </Button>
                )}
              </div>
            </div>
            {editing === u.id && (
              <EditUser u={u} onError={setErr} onSaved={() => { setEditing(null); reload() }} />
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}

function UserForm({ people, onSaved, onError }: { people: Person[]; onSaved: () => void; onError: (s: string | null) => void }) {
  const [f, setF] = useState({
    username: '', display_name: '', role: 'user', is_child_account: false, colour: '#4A90E2',
    avatar: '', pin: '', pin_confirm: '', password: '', password_confirm: '',
    personMode: 'new' as 'new' | 'existing' | 'none', link_person_id: '',
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    onError(null)
    if (!f.username.trim() || !f.display_name.trim()) return
    if (f.pin && f.pin !== f.pin_confirm) { onError('PINs do not match.'); return }
    if (f.password && f.password !== f.password_confirm) { onError('Passwords do not match.'); return }
    setSaving(true)
    try {
      await api.createUser({
        username: f.username.trim(), display_name: f.display_name.trim(), role: f.role,
        is_child_account: f.is_child_account, colour: f.colour, avatar: f.avatar,
        pin: f.pin || undefined, password: f.password || undefined,
        create_person: f.personMode === 'new',
        link_person_id: f.personMode === 'existing' && f.link_person_id ? Number(f.link_person_id) : undefined,
      })
      onSaved()
    } catch (e2) {
      onError(e2 instanceof Error ? cleanErr(e2.message) : 'Could not create user.')
    } finally { setSaving(false) }
  }

  return (
    <Card title="New user">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input className={input} placeholder="Username (login)" value={f.username} onChange={e => set('username', e.target.value)} />
        <input className={input} placeholder="Display name" value={f.display_name} onChange={e => set('display_name', e.target.value)} />
        <select className={input} value={f.role} onChange={e => set('role', e.target.value)}>
          {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="color" value={f.colour} onChange={e => set('colour', e.target.value)} /> Accent colour
        </label>
        <div className="sm:col-span-2">
          <EmojiPicker value={f.avatar} colour={f.colour} onChange={e => set('avatar', e)} />
        </div>
        <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="PIN (4–6 digits)" value={f.pin} onChange={e => set('pin', e.target.value)} />
        <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Confirm PIN" value={f.pin_confirm} onChange={e => set('pin_confirm', e.target.value)} />
        <input className={input} type="password" autoComplete="new-password" placeholder="Password (adults; for re-auth)" value={f.password} onChange={e => set('password', e.target.value)} />
        <input className={input} type="password" autoComplete="new-password" placeholder="Confirm password" value={f.password_confirm} onChange={e => set('password_confirm', e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-ink sm:col-span-2">
          <input type="checkbox" checked={f.is_child_account} onChange={e => set('is_child_account', e.target.checked)} />
          Child account (PIN only, no password)
        </label>

        <fieldset className="sm:col-span-2 border border-line rounded-xl p-3">
          <legend className="text-xs text-muted px-1">Household person</legend>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="radio" checked={f.personMode === 'new'} onChange={() => set('personMode', 'new')} />
              Create a new person with this name
            </label>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="radio" checked={f.personMode === 'existing'} onChange={() => set('personMode', 'existing')} />
              Link an existing person
              {f.personMode === 'existing' && (
                <select className={`${input} ml-2`} value={f.link_person_id} onChange={e => set('link_person_id', e.target.value)}>
                  <option value="">Select…</option>
                  {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                </select>
              )}
            </label>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="radio" checked={f.personMode === 'none'} onChange={() => set('personMode', 'none')} />
              No person (login only)
            </label>
          </div>
        </fieldset>

        <div className="sm:col-span-2">
          <Button type="submit" loading={saving} disabled={!f.username.trim() || !f.display_name.trim()}>Create user</Button>
        </div>
      </form>
    </Card>
  )
}

function EditUser({ u, onSaved, onError }: { u: AdminUser; onSaved: () => void; onError: (s: string | null) => void }) {
  const [f, setF] = useState({ display_name: u.display_name, role: u.role, colour: u.colour || '#4A90E2', avatar: u.avatar || '', pin: '', pin_confirm: '', password: '', password_confirm: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const save = async () => {
    onError(null)
    if (f.pin && f.pin !== f.pin_confirm) { onError('PINs do not match.'); return }
    if (f.password && f.password !== f.password_confirm) { onError('Passwords do not match.'); return }
    setSaving(true)
    try {
      await api.updateUser(u.id, {
        display_name: f.display_name, role: f.role, colour: f.colour, avatar: f.avatar,
        pin: f.pin || undefined, password: f.password || undefined,
      })
      onSaved()
    } catch (e) {
      onError(e instanceof Error ? cleanErr(e.message) : 'Could not save.')
    } finally { setSaving(false) }
  }

  return (
    <div className="mt-3 pt-3 border-t border-line grid grid-cols-1 sm:grid-cols-2 gap-3">
      <input className={input} value={f.display_name} onChange={e => set('display_name', e.target.value)} placeholder="Display name" />
      <select className={input} value={f.role} onChange={e => set('role', e.target.value)}>
        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Reset PIN (blank = keep)" value={f.pin} onChange={e => set('pin', e.target.value)} />
      <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Confirm new PIN" value={f.pin_confirm} onChange={e => set('pin_confirm', e.target.value)} />
      <input className={input} type="password" autoComplete="new-password" placeholder="Reset password (blank = keep)" value={f.password} onChange={e => set('password', e.target.value)} />
      <input className={input} type="password" autoComplete="new-password" placeholder="Confirm new password" value={f.password_confirm} onChange={e => set('password_confirm', e.target.value)} />
      <div className="sm:col-span-2 flex items-center gap-3">
        <input type="color" value={f.colour} onChange={e => set('colour', e.target.value)}
          className="w-10 h-10 rounded-lg border border-line cursor-pointer p-0.5 flex-shrink-0" title="Accent colour" />
        <span className="text-sm text-muted-strong">Accent colour</span>
        <div className="flex-1" />
        <EmojiPicker value={f.avatar} colour={f.colour} onChange={e => set('avatar', e)} />
      </div>
      <div className="sm:col-span-2"><Button size="sm" loading={saving} onClick={save}>Save changes</Button></div>
    </div>
  )
}

function cleanErr(msg: string): string {
  try {
    const json = JSON.parse(msg.slice(msg.indexOf('{')))
    if (json.detail) return typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail)
    return Object.values(json).flat().join(' ')
  } catch { return 'Something went wrong.' }
}
