import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type {
  MeridianGoal, MeridianWishlistItem, MeridianWishlistRequest, Person,
} from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { Field, Input, Textarea, fieldClass } from '../../../../components/ui'
import { useAuth } from '../../../auth/AuthContext'
import { confirmDialog, promptDialog } from '../../../../components/Dialogs'

// Shared bits ---------------------------------------------------------------

const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

function Progress({ pct }: { pct: number }) {
  return (
    <div className="h-2.5 rounded-full bg-sunken overflow-hidden">
      <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  )
}

function Contribute({ onContribute, disabled }: { onContribute: (n: number) => Promise<void>; disabled?: boolean }) {
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const go = async () => {
    const n = Number(amount)
    if (!n || n <= 0) return
    setBusy(true)
    try { await onContribute(n); setAmount('') } finally { setBusy(false) }
  }
  return (
    <div className="flex gap-2">
      <input type="number" min="1" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Points"
        className={`${fieldClass} !w-24`} />
      <Button size="sm" loading={busy} disabled={disabled} onClick={go}>Contribute</Button>
    </div>
  )
}

function useMyBalance() {
  const { user } = useAuth()
  const [personId, setPersonId] = useState<number | undefined>()
  const [balance, setBalance] = useState<number | null>(null)
  const refresh = async () => {
    const [ppl, pts] = await Promise.all([
      api.getPeople(),
      api.getMeridianPoints(),
    ])
    const mine = ppl.find(p => p.linked_user_id === user?.id)
    setPersonId(mine?.id)
    const row = pts.summary.find(s => s.person_id === mine?.id)
    setBalance(mine ? (row ? row.balance : 0) : null)
    return ppl
  }
  return { personId, balance, refresh, setBalance }
}

// Group goals ---------------------------------------------------------------

export function GoalsTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const [goals, setGoals] = useState<MeridianGoal[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const { balance, refresh } = useMyBalance()
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setError(null)
    try {
      await refresh()
      setGoals(await api.getMeridianGoals())
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        {balance !== null && <span className="text-sm text-muted">Your balance: <strong className="text-primary">★ {balance}</strong></span>}
        {canManage && (
          <Button size="sm" variant="secondary" className="ml-auto" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Close' : 'New goal'}
          </Button>
        )}
      </div>
      {error && <p className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
      {msg && <p className="text-sm text-primary text-center">{msg}</p>}
      {canManage && showForm && <NewGoalForm onCreated={() => { setShowForm(false); void reload() }} />}

      {goals.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No group goals yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {goals.map(g => (
            <Card key={g.id}>
              <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-ink">{g.title}</h3>
                  {canManage && (
                    <button
                      type="button"
                      aria-label={`Delete ${g.title}`}
                      onClick={async () => {
                        if (!(await confirmDialog({ title: `Delete "${g.title}"?`, confirmLabel: 'Delete' }))) return
                        setError(null)
                        try { await api.deleteMeridianGoal(g.id); await reload() } catch (e) { setError(errMsg(e)) }
                      }}
                      className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger"
                    >
                      ×
                    </button>
                  )}
                </div>
                {g.description && <p className="text-sm text-muted">{g.description}</p>}
                <Progress pct={g.progress_percentage} />
                <p className="text-xs text-muted">
                  <strong className="text-ink">{g.total_contributed}</strong> / {g.target_points} {pointsLabel}
                  {g.status === 'funded' ? ' · 🎉 Funded!' : ` · ${g.remaining_points} to go`}
                </p>
                {g.store_url && <a href={g.store_url} target="_blank" rel="noreferrer" className="text-xs text-primary underline">View in store →</a>}
                {g.status === 'active' && (
                  <Contribute
                    disabled={balance === 0}
                    onContribute={async n => {
                      setMsg(null); setError(null)
                      try { await api.contributeToGoal(g.id, n); await reload() }
                      catch (e) { setError(errMsg(e)) }
                    }}
                  />
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function NewGoalForm({ onCreated }: { onCreated: () => void }) {
  const [f, setF] = useState({ title: '', target_points: '100', description: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true); setError(null)
    try {
      await api.createMeridianGoal({ title: f.title.trim(), target_points: Number(f.target_points) || 0, description: f.description })
      onCreated()
    } catch (e2) {
      setError(errMsg(e2))
    } finally { setSaving(false) }
  }
  return (
    <Card title="New group goal">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {error && <p className="sm:col-span-2 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <Field label="Goal name"><Input autoFocus placeholder="e.g. Family movie night" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} /></Field>
        <Field label="Target" hint="Total household points needed."><Input type="number" min="1" inputMode="numeric" value={f.target_points} onChange={e => setF({ ...f, target_points: e.target.value })} /></Field>
        <Field label="Description" className="sm:col-span-2"><Textarea placeholder="What are you working towards together?" value={f.description} onChange={e => setF({ ...f, description: e.target.value })} /></Field>
        <div className="sm:col-span-2"><Button type="submit" loading={saving} disabled={!f.title.trim()}>Create goal</Button></div>
      </form>
    </Card>
  )
}

// Wishlist ------------------------------------------------------------------

export function WishlistTab({ canManage, pointsLabel, focusedWishId }: { canManage: boolean; pointsLabel: string; focusedWishId?: number }) {
  const [items, setItems] = useState<MeridianWishlistItem[]>([])
  const [requests, setRequests] = useState<MeridianWishlistRequest[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const { personId, balance, refresh } = useMyBalance()
  const [reqName, setReqName] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requestBusy, setRequestBusy] = useState(false)

  const reload = async () => {
    setError(null)
    try {
      const ppl = await refresh()
      setPeople(ppl)
      const [it, rq] = await Promise.all([
        api.getWishlistItems(),
        canManage ? api.getWishlistRequests('requested') : Promise.resolve([]),
      ])
      setItems(it); setRequests(rq)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!loading && focusedWishId) window.setTimeout(() => document.getElementById(`meridian-wish-${focusedWishId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }, [loading, focusedWishId])

  const personName = (id: number) => people.find(p => p.id === id)?.display_name || 'Someone'

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 flex-wrap">
        {balance !== null && <span className="text-sm text-muted">Your balance: <strong className="text-primary">★ {balance}</strong></span>}
      </div>
      {error && <p className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
      {msg && <p className="text-sm text-primary text-center">{msg}</p>}

      {/* Request a new item (anyone with a person) */}
      {personId && (
        <Card title="Ask for a wishlist item">
          <form className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end" onSubmit={async e => {
            e.preventDefault()
            if (!reqName.trim()) return
            setRequestBusy(true); setError(null); setMsg(null)
            try {
              await api.requestWishlistItem({ requested_name: reqName.trim() })
              setReqName(''); setMsg('Requested — a household manager will set it up.'); await reload()
            } catch (e2) {
              setError(errMsg(e2))
            } finally {
              setRequestBusy(false)
            }
          }}>
            <Field label="Wishlist item"><Input autoFocus value={reqName} onChange={e => setReqName(e.target.value)} placeholder="What would you like?" /></Field>
            <Button type="submit" loading={requestBusy} disabled={!reqName.trim()}>Send request</Button>
          </form>
        </Card>
      )}

      {/* Admin: pending requests → approve with a point cost */}
      {canManage && requests.length > 0 && (
        <Card title="Wishlist requests">
          <ul className="flex flex-col gap-2">
            {requests.map(r => (
              <li key={r.id} className="flex flex-col gap-3 rounded-xl bg-sunken p-3 sm:flex-row sm:items-center sm:justify-between">
                <span className="text-sm text-ink">{personName(r.person_id)} · {r.requested_name}</span>
                <div className="grid grid-cols-2 gap-2 sm:flex">
                  <Button size="sm" onClick={async () => {
                    const answer = await promptDialog({
                      title: `Approve "${r.requested_name}"`, label: 'Point cost',
                      defaultValue: '50', inputMode: 'numeric', confirmLabel: 'Approve', required: true,
                    })
                    if (answer === null) return
                    const cost = Number(answer)
                    if (!(cost > 0)) { setError('Enter a point cost above zero.'); return }
                    setError(null)
                    try { await api.approveWishlistRequest(r.id, cost); await reload() } catch (e) { setError(errMsg(e)) }
                  }}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={async () => {
                    setError(null)
                    try { await api.rejectWishlistRequest(r.id); await reload() } catch (e) { setError(errMsg(e)) }
                  }}>Reject</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {items.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No wishlist items yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map(it => (
            <div key={it.id} id={`meridian-wish-${it.id}`} className={focusedWishId === it.id ? 'rounded-2xl ring-2 ring-primary ring-offset-2 ring-offset-paper' : ''}><Card>
              <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-ink">{it.name} <span className="text-xs text-muted font-normal">· {personName(it.person_id)}</span></h3>
                  {canManage && (
                    <button
                      type="button"
                      aria-label={`Delete ${it.name}`}
                      onClick={async () => {
                        if (!(await confirmDialog({ title: `Delete "${it.name}"?`, confirmLabel: 'Delete' }))) return
                        setError(null)
                        try { await api.deleteWishlistItem(it.id); await reload() } catch (e) { setError(errMsg(e)) }
                      }}
                      className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger"
                    >
                      ×
                    </button>
                  )}
                </div>
                <Progress pct={it.progress_percentage} />
                <p className="text-xs text-muted">
                  <strong className="text-ink">{it.total_saved}</strong> / {it.point_cost} {pointsLabel}
                  {it.status === 'fulfilled' ? ' · ✅ Fulfilled' : it.status === 'funded' ? ' · 🎉 Funded!' : ` · ${it.remaining_points} to go`}
                </p>
                {it.status === 'active' && it.person_id === personId && (
                  <Contribute disabled={balance === 0} onContribute={async n => {
                    setMsg(null); setError(null)
                    try { await api.contributeToWishlist(it.id, n); await reload() }
                    catch (e) { setError(errMsg(e)) }
                  }} />
                )}
                {canManage && it.status === 'funded' && (
                  <Button size="sm" variant="secondary" onClick={async () => {
                    setError(null)
                    try { await api.fulfillWishlistItem(it.id); await reload() } catch (e) { setError(errMsg(e)) }
                  }}>Mark fulfilled</Button>
                )}
              </div>
            </Card></div>
          ))}
        </div>
      )}
    </div>
  )
}
