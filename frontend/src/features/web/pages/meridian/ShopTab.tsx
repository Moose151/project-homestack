import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianReward, MeridianRewardRequest, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { useAuth } from '../../../auth/AuthContext'

// Mirrors the legacy shop.html: balance banner, product cards with image, cost, stock and
// price/store links, a client-side cart + checkout, and admin management + pending approvals.

export function ShopTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const { user } = useAuth()
  const [rewards, setRewards] = useState<MeridianReward[]>([])
  const [requests, setRequests] = useState<MeridianRewardRequest[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [cart, setCart] = useState<number[]>([])
  const [showForm, setShowForm] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const reload = async () => {
    const [r, p, pts, reqs] = await Promise.all([
      api.getMeridianRewards(),
      api.getPeople().catch(() => []),
      api.getMeridianPoints().catch(() => ({ summary: [], entries: [] })),
      canManage ? api.getMeridianRewardRequests('pending') : Promise.resolve([]),
    ])
    setRewards(r); setPeople(p); setRequests(reqs)
    const myPerson = p.find(x => x.linked_user_id === user?.id)
    const row = pts.summary.find(s => s.person_id === myPerson?.id)
    setBalance(myPerson ? (row ? row.balance : 0) : null)
    setLoading(false)
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const cartCount = cart.length
  const cartTotal = cart.reduce((sum, id) => sum + (rewards.find(r => r.id === id)?.cost_points || 0), 0)

  const addToCart = (r: MeridianReward) => {
    if (!r.allow_multiple_in_cart && cart.includes(r.id)) return
    setCart(prev => [...prev, r.id])
  }
  const removeFromCart = (id: number) => setCart(prev => {
    const i = prev.indexOf(id)
    return i < 0 ? prev : [...prev.slice(0, i), ...prev.slice(i + 1)]
  })

  const checkout = async () => {
    setMsg(null)
    try {
      await api.checkoutCart(cart)
      setCart([])
      setMsg('Sent for approval! 🎉')
      await reload()
    } catch {
      setMsg('Could not check out — not enough points, out of stock, or a daily limit was hit.')
    }
  }

  const act = async (fn: Promise<unknown>) => { await fn.catch(() => {}); await reload() }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          {balance !== null && (
            <div>
              <p className="text-xs text-muted uppercase tracking-wide">Your {pointsLabel}</p>
              <p className="text-2xl font-extrabold text-primary">★ {balance}</p>
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            {cartCount > 0 && <span className="text-sm text-muted-strong">🛒 {cartCount} · ★ {cartTotal}</span>}
            {cartCount > 0 && <Button size="sm" onClick={checkout}>Check out</Button>}
            {canManage && (
              <Button size="sm" variant="secondary" onClick={() => setShowForm(s => !s)}>
                {showForm ? 'Close' : 'New reward'}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {msg && <p className="text-sm text-primary text-center">{msg}</p>}

      {canManage && showForm && <NewRewardForm onCreated={() => { setShowForm(false); reload() }} />}

      {canManage && requests.length > 0 && (
        <Card title="Pending reward requests">
          <ul className="flex flex-col gap-2">
            {requests.map(req => (
              <li key={req.id} className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">
                  {people.find(p => p.id === req.requested_by_person_id)?.display_name || 'Someone'}
                  {' · '}{rewards.find(r => r.id === req.reward_id)?.name || `#${req.reward_id}`}
                  {' · ★ '}{req.points_spent}
                </span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => act(api.approveMeridianRewardRequest(req.id))}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={() => act(api.rejectMeridianRewardRequest(req.id))}>Reject</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {cartCount > 0 && (
        <Card title="Your cart">
          <ul className="flex flex-col gap-1.5">
            {cart.map((id, idx) => {
              const r = rewards.find(x => x.id === id)
              return (
                <li key={`${id}-${idx}`} className="flex items-center justify-between text-sm">
                  <span className="text-ink">{r?.name} · ★ {r?.cost_points}</span>
                  <button className="text-muted hover:text-danger" onClick={() => removeFromCart(id)}>remove</button>
                </li>
              )
            })}
          </ul>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {rewards.map(r => {
          const outOfStock = r.remaining_stock !== null && r.remaining_stock <= 0
          const cantAfford = !canManage && balance !== null && balance < r.cost_points
          return (
            <Card key={r.id} className={r.is_archived ? 'opacity-60' : ''}>
              {r.image_url && (
                <img src={r.image_url} alt={r.name}
                  className="-mx-5 -mt-3 mb-3 h-36 w-[calc(100%+2.5rem)] object-cover rounded-t-2xl" />
              )}
              <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-ink">{r.name}</h3>
                  <span className="text-sm font-bold text-primary whitespace-nowrap">★ {r.cost_points}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {r.is_archived && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted">Hidden</span>}
                  {r.remaining_stock !== null && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${outOfStock ? 'bg-danger-soft text-danger' : 'bg-sunken text-muted-strong'}`}>
                      {outOfStock ? 'Out of stock' : `${r.remaining_stock} left`}
                    </span>
                  )}
                </div>
                {r.description && <p className="text-sm text-muted">{r.description}</p>}
                {(r.price_estimate || r.store_url) && (
                  <p className="text-xs text-muted flex gap-3">
                    {r.price_estimate && <span>💰 {r.price_estimate}</span>}
                    {r.store_url && <a className="text-primary underline" href={r.store_url} target="_blank" rel="noreferrer">View</a>}
                  </p>
                )}
                <div className="flex gap-2 mt-1 items-center">
                  <Button size="sm" disabled={outOfStock || cantAfford} onClick={() => addToCart(r)}>
                    {cantAfford ? 'Not enough' : 'Add to cart'}
                  </Button>
                  {canManage && (
                    <button onClick={() => { if (confirm(`Delete "${r.name}"?`)) act(api.deleteMeridianReward(r.id)) }}
                      className="text-muted hover:text-danger text-lg leading-none ml-auto" aria-label="Delete">×</button>
                  )}
                </div>
              </div>
            </Card>
          )
        })}
        {rewards.length === 0 && <p className="text-sm text-muted text-center py-8 sm:col-span-3">No rewards yet.</p>}
      </div>
    </div>
  )
}

function NewRewardForm({ onCreated }: { onCreated: () => void }) {
  const [f, setF] = useState({
    name: '', cost_points: '20', description: '', image_url: '', price_estimate: '',
    store_url: '', quantity: '', daily_limit_per_user: '', allow_multiple_in_cart: false,
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))
  const input = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.name.trim()) return
    setSaving(true)
    try {
      const reward = await api.createMeridianReward({
        name: f.name.trim(), cost_points: Number(f.cost_points) || 0, description: f.description,
      })
      // The create endpoint takes the core fields; apply shop extras via PATCH.
      await api.updateMeridianReward(reward.id, {
        image_url: f.image_url, price_estimate: f.price_estimate, store_url: f.store_url,
        quantity: f.quantity === '' ? null : Number(f.quantity),
        daily_limit_per_user: f.daily_limit_per_user === '' ? null : Number(f.daily_limit_per_user),
        allow_multiple_in_cart: f.allow_multiple_in_cart,
      }).catch(() => {})
      onCreated()
    } finally { setSaving(false) }
  }

  return (
    <Card title="New reward">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input className={input} placeholder="Reward name…" value={f.name} onChange={e => set('name', e.target.value)} />
        <input className={input} type="number" min="0" placeholder="Cost (points)" value={f.cost_points} onChange={e => set('cost_points', e.target.value)} />
        <textarea className={`${input} sm:col-span-2`} placeholder="Description" value={f.description} onChange={e => set('description', e.target.value)} />
        <input className={input} placeholder="Image URL (optional)" value={f.image_url} onChange={e => set('image_url', e.target.value)} />
        <input className={input} placeholder="Price estimate (e.g. $9.99)" value={f.price_estimate} onChange={e => set('price_estimate', e.target.value)} />
        <input className={input} placeholder="Store URL (optional)" value={f.store_url} onChange={e => set('store_url', e.target.value)} />
        <input className={input} type="number" min="0" placeholder="Stock (blank = unlimited)" value={f.quantity} onChange={e => set('quantity', e.target.value)} />
        <input className={input} type="number" min="0" placeholder="Daily limit per person (blank = none)" value={f.daily_limit_per_user} onChange={e => set('daily_limit_per_user', e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.allow_multiple_in_cart} onChange={e => set('allow_multiple_in_cart', e.target.checked)} /> Allow multiple in cart
        </label>
        <div className="sm:col-span-2"><Button type="submit" loading={saving} disabled={!f.name.trim()}>Create reward</Button></div>
      </form>
    </Card>
  )
}
