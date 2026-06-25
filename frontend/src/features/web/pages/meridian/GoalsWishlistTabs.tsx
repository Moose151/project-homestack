import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type {
  MeridianGoal, MeridianWishlistItem, MeridianWishlistRequest, Person,
} from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { useAuth } from '../../../auth/AuthContext'

// Shared bits ---------------------------------------------------------------

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
        className="w-24 px-3 py-1.5 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary" />
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
      api.getPeople().catch(() => []),
      api.getMeridianPoints().catch(() => ({ summary: [], entries: [] })),
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

  const reload = async () => {
    await refresh()
    setGoals(await api.getMeridianGoals().catch(() => []))
    setLoading(false)
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
      {msg && <p className="text-sm text-primary text-center">{msg}</p>}
      {canManage && showForm && <NewGoalForm onCreated={() => { setShowForm(false); reload() }} />}

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
                    <button onClick={() => { if (confirm(`Delete "${g.title}"?`)) api.deleteMeridianGoal(g.id).then(reload) }}
                      className="text-muted hover:text-danger text-lg leading-none">×</button>
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
                      setMsg(null)
                      try { await api.contributeToGoal(g.id, n); await reload() }
                      catch { setMsg('Could not contribute — not enough points.') }
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
  const input = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    try {
      await api.createMeridianGoal({ title: f.title.trim(), target_points: Number(f.target_points) || 0, description: f.description })
      onCreated()
    } finally { setSaving(false) }
  }
  return (
    <Card title="New group goal">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input className={input} placeholder="Goal (e.g. Family movie night)" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} />
        <input className={input} type="number" min="0" placeholder="Target points" value={f.target_points} onChange={e => setF({ ...f, target_points: e.target.value })} />
        <input className={`${input} sm:col-span-2`} placeholder="Description (optional)" value={f.description} onChange={e => setF({ ...f, description: e.target.value })} />
        <div className="sm:col-span-2"><Button type="submit" loading={saving} disabled={!f.title.trim()}>Create goal</Button></div>
      </form>
    </Card>
  )
}

// Wishlist ------------------------------------------------------------------

export function WishlistTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const [items, setItems] = useState<MeridianWishlistItem[]>([])
  const [requests, setRequests] = useState<MeridianWishlistRequest[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const { personId, balance, refresh } = useMyBalance()
  const [reqName, setReqName] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  const reload = async () => {
    const ppl = await refresh()
    setPeople(ppl)
    const [it, rq] = await Promise.all([
      api.getWishlistItems().catch(() => []),
      canManage ? api.getWishlistRequests('requested').catch(() => []) : Promise.resolve([]),
    ])
    setItems(it); setRequests(rq); setLoading(false)
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const personName = (id: number) => people.find(p => p.id === id)?.display_name || 'Someone'

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 flex-wrap">
        {balance !== null && <span className="text-sm text-muted">Your balance: <strong className="text-primary">★ {balance}</strong></span>}
      </div>
      {msg && <p className="text-sm text-primary text-center">{msg}</p>}

      {/* Request a new item (anyone with a person) */}
      {personId && (
        <Card title="Ask for a wishlist item">
          <form className="flex gap-2" onSubmit={async e => {
            e.preventDefault()
            if (!reqName.trim()) return
            await api.requestWishlistItem({ requested_name: reqName.trim() }).catch(() => {})
            setReqName(''); setMsg('Requested — a parent will set it up.'); reload()
          }}>
            <input value={reqName} onChange={e => setReqName(e.target.value)} placeholder="What would you like?"
              className="flex-1 px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary" />
            <Button size="sm" type="submit" disabled={!reqName.trim()}>Request</Button>
          </form>
        </Card>
      )}

      {/* Admin: pending requests → approve with a point cost */}
      {canManage && requests.length > 0 && (
        <Card title="Wishlist requests">
          <ul className="flex flex-col gap-2">
            {requests.map(r => (
              <li key={r.id} className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">{personName(r.person_id)} · {r.requested_name}</span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={async () => {
                    const cost = Number(prompt(`Point cost for "${r.requested_name}"?`, '50'))
                    if (cost > 0) { await api.approveWishlistRequest(r.id, cost).catch(() => {}); reload() }
                  }}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={() => api.rejectWishlistRequest(r.id).then(reload)}>Reject</Button>
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
            <Card key={it.id}>
              <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-ink">{it.name} <span className="text-xs text-muted font-normal">· {personName(it.person_id)}</span></h3>
                  {canManage && (
                    <button onClick={() => { if (confirm(`Delete "${it.name}"?`)) api.deleteWishlistItem(it.id).then(reload) }}
                      className="text-muted hover:text-danger text-lg leading-none">×</button>
                  )}
                </div>
                <Progress pct={it.progress_percentage} />
                <p className="text-xs text-muted">
                  <strong className="text-ink">{it.total_saved}</strong> / {it.point_cost} {pointsLabel}
                  {it.status === 'fulfilled' ? ' · ✅ Fulfilled' : it.status === 'funded' ? ' · 🎉 Funded!' : ` · ${it.remaining_points} to go`}
                </p>
                {it.status === 'active' && it.person_id === personId && (
                  <Contribute disabled={balance === 0} onContribute={async n => {
                    setMsg(null)
                    try { await api.contributeToWishlist(it.id, n); await reload() }
                    catch { setMsg('Could not contribute — not enough points.') }
                  }} />
                )}
                {canManage && it.status === 'funded' && (
                  <Button size="sm" variant="secondary" onClick={() => api.fulfillWishlistItem(it.id).then(reload)}>Mark fulfilled</Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
