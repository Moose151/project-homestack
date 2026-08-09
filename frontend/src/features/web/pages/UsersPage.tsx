import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { AdminUser, Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Avatar } from '../../../components/Avatar'
import { useAuth } from '../../auth/AuthContext'
import { PageHeader } from '../../../components/PageHeader'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'

const ROLES = ['admin', 'manager', 'user', 'guest'] as const
const ROLE_LABEL: Record<(typeof ROLES)[number], string> = {
  admin: 'Administrator',
  manager: 'Household manager',
  user: 'Household member',
  guest: 'Guest',
}
const ROLE_HELP: Record<(typeof ROLES)[number], string> = {
  admin: 'Full system, account and household settings access.',
  manager: 'Recommended for a trusted adult partner. Can manage normal household records.',
  user: 'Can use normal household features but cannot administer other people.',
  guest: 'Mostly read-only access for a temporary household guest.',
}
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
  const { user, logout } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const reload = async () => {
    setLoading(true)
    try {
      const [u, p] = await Promise.all([api.getUsers(), api.getPeople()])
      setUsers(u)
      setPeople(p)
      setErr(null)
    } catch (e) {
      const message = e instanceof Error ? e.message : ''
      if (/\b401\b|Authentication credentials were not provided/i.test(message)) {
        await logout()
        return
      }
      setErr(e instanceof Error ? cleanErr(e.message) : 'Could not load users.')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { reload() }, [])

  if (user?.role !== 'admin') {
    return <p className="text-sm text-muted">Only admins can manage users.</p>
  }
  if (loading) return <PageSkeleton cards={2} />

  const unlinkedPeople = people.filter(p => p.linked_user_id == null)

  return (
    <div className="flex flex-col gap-5">
      <div className="hidden sm:block">
        <PageHeader
          title="People & access"
          icon="👥"
          subtitle="Manage profiles, roles, login PINs and re-authentication passwords."
          actions={<Button size="sm" onClick={() => { setShowForm(s => !s); setErr(null) }}>
            {showForm ? 'Close' : 'Add household login'}
          </Button>}
        />
      </div>
      <div className="flex items-center justify-between gap-3 sm:hidden">
        <p className="text-xs font-medium text-muted">Household accounts and access</p>
        <Button size="sm" onClick={() => { setShowForm(s => !s); setErr(null) }}>{showForm ? 'Close' : '+ Add login'}</Button>
      </div>

      {err && <InlineAlert message={err} onRetry={reload} onDismiss={() => setErr(null)} />}

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
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${ROLE_BADGE[u.role]}`}>{ROLE_LABEL[u.role]}</span>
                  {u.solace_access && <span className="rounded-full bg-success-soft px-2 py-0.5 text-xs font-semibold text-success">Money access</span>}
                  {!u.has_password && !u.is_child_account && <span className="rounded-full bg-warning-soft px-2 py-0.5 text-xs font-semibold text-warning">Password needed</span>}
                  {u.is_child_account && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">child</span>}
                  {!u.is_active && <span className="text-xs px-2 py-0.5 rounded-full bg-danger-soft text-danger">inactive</span>}
                </div>
                {u.linked_person_name && <p className="text-xs text-muted mt-0.5">Person: {u.linked_person_name}</p>}
              </div>
              <div className="flex w-full gap-2 sm:w-auto">
                <Button size="sm" variant="ghost" onClick={() => setEditing(editing === u.id ? null : u.id)}>
                  {editing === u.id ? 'Close' : 'Edit'}
                </Button>
                {u.is_active && u.id !== user.id && (
                  <Button size="sm" variant="ghost" className="flex-1 sm:flex-none"
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
    username: '', display_name: '', role: 'manager', is_child_account: false, solace_access: false, colour: '#4A90E2',
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
    if (f.solace_access && !f.password) { onError('Set a password before allowing Money access.'); return }
    setSaving(true)
    try {
      await api.createUser({
        username: f.username.trim(), display_name: f.display_name.trim(), role: f.role,
        is_child_account: f.is_child_account, colour: f.colour, avatar: f.avatar,
        pin: f.pin || undefined, password: f.password || undefined,
        solace_access: f.solace_access,
        create_person: f.personMode === 'new',
        link_person_id: f.personMode === 'existing' && f.link_person_id ? Number(f.link_person_id) : undefined,
      })
      onSaved()
    } catch (e2) {
      onError(e2 instanceof Error ? cleanErr(e2.message) : 'Could not create user.')
    } finally { setSaving(false) }
  }

  return (
    <Card title="Add a household login">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="rounded-xl bg-primary-soft px-3 py-2.5 text-sm text-primary sm:col-span-2">
          For a partner, choose <strong>Household manager</strong>, set both a PIN and password,
          then deliberately choose whether they can open Money.
        </div>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Login name
          <input className={input} placeholder="e.g. alex" value={f.username} onChange={e => set('username', e.target.value)} autoFocus />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Name shown in HomeStack
          <input className={input} placeholder="Display name" value={f.display_name} onChange={e => set('display_name', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Access level
          <select className={input} value={f.role} disabled={f.is_child_account} onChange={e => set('role', e.target.value)}>
            {ROLES.map(r => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
          <span className="font-normal normal-case text-muted">{ROLE_HELP[f.role as (typeof ROLES)[number]]}</span>
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="color" value={f.colour} onChange={e => set('colour', e.target.value)} /> Accent colour
        </label>
        <details className="rounded-xl border border-line sm:col-span-2">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-3 text-sm font-semibold text-muted-strong">Choose an account picture <span>▾</span></summary>
          <div className="border-t border-line p-3"><EmojiPicker value={f.avatar} colour={f.colour} onChange={e => set('avatar', e)} /></div>
        </details>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">PIN for everyday sign-in
          <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="4–6 digits" value={f.pin} onChange={e => set('pin', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Confirm PIN
          <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Repeat PIN" value={f.pin_confirm} onChange={e => set('pin_confirm', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Password for protected actions
          <input className={input} type="password" autoComplete="new-password" placeholder="Adult account password" value={f.password} onChange={e => set('password', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Confirm password
          <input className={input} type="password" autoComplete="new-password" placeholder="Repeat password" value={f.password_confirm} onChange={e => set('password_confirm', e.target.value)} />
        </label>
        <label className="flex items-center gap-2 text-sm text-ink sm:col-span-2">
          <input type="checkbox" checked={f.is_child_account} onChange={e => { set('is_child_account', e.target.checked); if (e.target.checked) { set('solace_access', false); set('role', 'user') } }} />
          Child account (PIN only, no password)
        </label>
        {!f.is_child_account && (
          <label className="rounded-xl border border-line p-3 sm:col-span-2">
            <span className="flex items-start gap-3">
              <input className="mt-1" type="checkbox" checked={f.solace_access} onChange={e => set('solace_access', e.target.checked)} />
              <span>
                <span className="block text-sm font-bold text-ink">Allow Money and home-finance access</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-muted">Grants this person access to Solace bills, pay plans and linked Homestead costs. Protected access still requires their password when the household setting is enabled.</span>
              </span>
            </span>
          </label>
        )}

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
  const [f, setF] = useState({
    display_name: u.display_name,
    role: u.role,
    solace_access: u.solace_access,
    colour: u.colour || '#4A90E2',
    avatar: u.avatar || '',
    pin: '', pin_confirm: '', password: '', password_confirm: '',
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const save = async () => {
    onError(null)
    if (f.pin && f.pin !== f.pin_confirm) { onError('PINs do not match.'); return }
    if (f.password && f.password !== f.password_confirm) { onError('Passwords do not match.'); return }
    if (f.solace_access && !u.has_password && !f.password) { onError('Set a password before allowing Money access.'); return }
    setSaving(true)
    try {
      await api.updateUser(u.id, {
        display_name: f.display_name, role: f.role, colour: f.colour, avatar: f.avatar,
        pin: f.pin || undefined, password: f.password || undefined, solace_access: f.solace_access,
      })
      onSaved()
    } catch (e) {
      onError(e instanceof Error ? cleanErr(e.message) : 'Could not save.')
    } finally { setSaving(false) }
  }

  return (
    <div className="mt-3 pt-3 border-t border-line grid grid-cols-1 sm:grid-cols-2 gap-3">
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Name shown in HomeStack
        <input className={input} value={f.display_name} onChange={e => set('display_name', e.target.value)} placeholder="Display name" />
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Access level
        <select className={input} value={f.role} disabled={u.is_child_account} onChange={e => set('role', e.target.value)}>
          {ROLES.map(r => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
        </select>
        <span className="font-normal normal-case text-muted">{ROLE_HELP[f.role as (typeof ROLES)[number]]}</span>
      </label>
      <label className="flex items-center gap-3 rounded-xl border border-line p-3 sm:col-span-2">
        <input
          type="checkbox"
          checked={f.solace_access}
          disabled={u.is_child_account || f.role === 'admin'}
          onChange={e => set('solace_access', e.target.checked)}
        />
        <span>
          <span className="block text-sm font-bold text-ink">Money and home-finance access</span>
          <span className="block text-xs text-muted">
            {f.role === 'admin' ? 'Administrators always have Money access.' : u.is_child_account ? 'Unavailable for child accounts.' : 'Includes Solace and linked Homestead costs; password protection still applies.'}
          </span>
        </span>
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Reset PIN
        <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Blank keeps current PIN" value={f.pin} onChange={e => set('pin', e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Confirm new PIN
        <input className={input} type="password" inputMode="numeric" autoComplete="new-password" placeholder="Repeat new PIN" value={f.pin_confirm} onChange={e => set('pin_confirm', e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Reset password
        <input className={input} type="password" autoComplete="new-password" placeholder="Blank keeps current password" value={f.password} onChange={e => set('password', e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Confirm new password
        <input className={input} type="password" autoComplete="new-password" placeholder="Repeat new password" value={f.password_confirm} onChange={e => set('password_confirm', e.target.value)} />
      </label>
      <label className="flex items-center gap-3 text-sm text-muted-strong sm:col-span-2">
        <input type="color" value={f.colour} onChange={e => set('colour', e.target.value)}
          className="h-10 w-10 flex-shrink-0 cursor-pointer rounded-lg border border-line p-0.5" />
        Accent colour
      </label>
      <details className="rounded-xl border border-line sm:col-span-2">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-3 text-sm font-semibold text-muted-strong">Change account picture <span>▾</span></summary>
        <div className="border-t border-line p-3"><EmojiPicker value={f.avatar} colour={f.colour} onChange={e => set('avatar', e)} /></div>
      </details>
      <div className="sm:col-span-2"><Button size="sm" loading={saving} onClick={save}>Save changes</Button></div>
    </div>
  )
}

function cleanErr(msg: string): string {
  if (!msg.includes('{')) return msg
  try {
    const json = JSON.parse(msg.slice(msg.indexOf('{')))
    if (json.detail) return typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail)
    return Object.values(json).flat().join(' ')
  } catch { return 'Something went wrong.' }
}
