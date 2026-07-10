import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianReward, MeridianRewardRequest, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { useAuth } from '../../../auth/AuthContext'

type RewardFilter = 'active' | 'pending' | 'stock' | 'hidden' | 'all'

const inputClass = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

function Badge({ children, className = 'bg-sunken text-muted-strong' }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${className}`}>{children}</span>
}

export function ShopTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const { user } = useAuth()
  const [rewards, setRewards] = useState<MeridianReward[]>([])
  const [requests, setRequests] = useState<MeridianRewardRequest[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<RewardFilter>('active')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [cart, setCart] = useState<number[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setError(null)
    try {
      const [rewardRows, peopleRows, points, requestRows] = await Promise.all([
        api.getMeridianRewards(),
        api.getPeople().catch(() => []),
        api.getMeridianPoints().catch(() => ({ summary: [], entries: [] })),
        canManage ? api.getMeridianRewardRequests('pending') : Promise.resolve([]),
      ])
      setRewards(rewardRows)
      setPeople(peopleRows)
      setRequests(requestRows)
      const myPerson = peopleRows.find(x => x.linked_user_id === user?.id)
      const row = points.summary.find(s => s.person_id === myPerson?.id)
      setBalance(myPerson ? (row ? row.balance : 0) : null)
    } catch {
      setError('Rewards could not be refreshed.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const personName = (id: number | null) => people.find(p => p.id === id)?.display_name || 'Someone'
  const rewardName = (id: number) => rewards.find(r => r.id === id)?.name || `Reward #${id}`
  const pendingByReward = useMemo(() => {
    const map = new Map<number, MeridianRewardRequest[]>()
    requests.forEach(r => map.set(r.reward_id, [...(map.get(r.reward_id) || []), r]))
    return map
  }, [requests])

  const visible = useMemo(() => rewards.filter(r => {
    const out = r.remaining_stock !== null && r.remaining_stock <= 0
    if (filter === 'active' && (!r.is_active || r.is_archived)) return false
    if (filter === 'pending' && !pendingByReward.has(r.id)) return false
    if (filter === 'stock' && !out) return false
    if (filter === 'hidden' && r.is_active && !r.is_archived) return false
    return true
  }), [rewards, filter, pendingByReward])

  const metrics = {
    active: rewards.filter(r => r.is_active && !r.is_archived).length,
    pending: requests.length,
    stock: rewards.filter(r => r.remaining_stock !== null && r.remaining_stock <= 0).length,
  }

  const act = async (work: Promise<unknown>) => {
    setError(null); setMessage(null)
    try {
      await work
      await reload()
    } catch {
      setError('That reward change did not save. Refresh and try again.')
    }
  }

  const addToCart = (reward: MeridianReward) => {
    if (!reward.allow_multiple_in_cart && cart.includes(reward.id)) return
    setCart(prev => [...prev, reward.id])
  }

  const checkout = async () => {
    setError(null); setMessage(null)
    try {
      await api.checkoutCart(cart)
      setCart([])
      setMessage('Reward request sent for approval.')
      await reload()
    } catch {
      setError('Could not check out. Check points, stock, and daily limits.')
    }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  if (!canManage) {
    return (
      <ShopperView
        rewards={rewards.filter(r => r.is_active && !r.is_archived)}
        balance={balance}
        pointsLabel={pointsLabel}
        cart={cart}
        onAdd={addToCart}
        onRemove={(id) => setCart(prev => removeOne(prev, id))}
        onCheckout={checkout}
        message={message}
        error={error}
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}
      {message && <div className="rounded-xl border border-success/30 bg-success-soft px-4 py-3 text-sm text-success">{message}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Metric label="Active rewards" value={String(metrics.active)} detail="Visible in the shop" />
        <Metric label="Pending requests" value={String(metrics.pending)} detail="Waiting for approval" />
        <Metric label="Out of stock" value={String(metrics.stock)} detail="Needs attention" />
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">View</span>
            <select value={filter} onChange={e => setFilter(e.target.value as RewardFilter)} className={inputClass}>
              <option value="active">Active rewards</option>
              <option value="pending">Needs approval</option>
              <option value="stock">Out of stock</option>
              <option value="hidden">Hidden or archived</option>
              <option value="all">All rewards</option>
            </select>
          </label>
          {filter !== 'active' && <Button size="sm" variant="ghost" onClick={() => setFilter('active')}>Clear</Button>}
          <Button size="sm" className="ml-auto" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Close' : 'New reward'}
          </Button>
        </div>
      </Card>

      {showForm && (
        <RewardForm
          onSaved={() => { setShowForm(false); reload() }}
          onError={() => setError('Reward could not be created.')}
        />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <Card title="Reward management">
          {visible.length === 0 ? (
            <p className="text-sm text-muted py-4">No rewards match this view.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-muted">
                    <th className="py-2 pr-3">Reward</th>
                    <th className="py-2 pr-3">Cost</th>
                    <th className="py-2 pr-3">Stock</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {visible.map(reward => (
                    editingId === reward.id ? (
                      <RewardEditRow
                        key={reward.id}
                        reward={reward}
                        onCancel={() => setEditingId(null)}
                        onSaved={() => { setEditingId(null); reload() }}
                        onError={() => setError('Reward could not be saved.')}
                      />
                    ) : (
                      <RewardRow
                        key={reward.id}
                        reward={reward}
                        pending={pendingByReward.get(reward.id) || []}
                        pointsLabel={pointsLabel}
                        personName={personName}
                        onEdit={() => setEditingId(reward.id)}
                        onToggleActive={() => act(api.updateMeridianReward(reward.id, { is_active: !reward.is_active }))}
                        onArchive={() => act(api.updateMeridianReward(reward.id, { is_archived: !reward.is_archived }))}
                        onDelete={() => { if (confirm(`Delete "${reward.name}"?`)) act(api.deleteMeridianReward(reward.id)) }}
                        onApprove={(id) => act(api.approveMeridianRewardRequest(id))}
                        onReject={(id) => act(api.rejectMeridianRewardRequest(id, prompt('Reason (optional)') || ''))}
                      />
                    )
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Pending requests">
          {requests.length === 0 ? (
            <p className="text-sm text-muted py-3">No reward requests waiting.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {requests.map(req => (
                <li key={req.id} className="py-3">
                  <p className="font-semibold text-ink">{rewardName(req.reward_id)}</p>
                  <p className="text-sm text-muted">{personName(req.requested_by_person_id)} · ★ {req.points_spent} {pointsLabel}</p>
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" onClick={() => act(api.approveMeridianRewardRequest(req.id))}>Approve</Button>
                    <Button size="sm" variant="ghost" onClick={() => act(api.rejectMeridianRewardRequest(req.id, prompt('Reason (optional)') || ''))}>Reject</Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function RewardRow({
  reward,
  pending,
  pointsLabel,
  personName,
  onEdit,
  onToggleActive,
  onArchive,
  onDelete,
  onApprove,
  onReject,
}: {
  reward: MeridianReward
  pending: MeridianRewardRequest[]
  pointsLabel: string
  personName: (id: number | null) => string
  onEdit: () => void
  onToggleActive: () => void
  onArchive: () => void
  onDelete: () => void
  onApprove: (id: number) => void
  onReject: (id: number) => void
}) {
  const out = reward.remaining_stock !== null && reward.remaining_stock <= 0
  return (
    <tr className="align-top">
      <td className="py-3 pr-3">
        <div className="flex gap-3">
          {reward.image_url ? (
            <img src={reward.image_url} alt="" className="h-12 w-12 rounded-lg object-cover border border-line" />
          ) : (
            <div className="h-12 w-12 rounded-lg border border-line bg-sunken" />
          )}
          <div className="min-w-0">
            <p className="font-semibold text-ink">{reward.name}</p>
            {reward.description && <p className="mt-0.5 max-w-xl text-xs text-muted line-clamp-2">{reward.description}</p>}
            <div className="mt-1 flex flex-wrap gap-1.5">
              {reward.store_url && <a className="text-xs font-semibold text-primary underline" href={reward.store_url} target="_blank" rel="noreferrer">Store</a>}
              {reward.price_estimate && <Badge>{reward.price_estimate}</Badge>}
              {reward.daily_limit_per_user !== null && <Badge>{reward.daily_limit_per_user}/day</Badge>}
              {reward.allow_multiple_in_cart && <Badge>Multiple allowed</Badge>}
            </div>
            {pending.length > 0 && (
              <div className="mt-2 flex flex-col gap-1.5">
                {pending.map(req => (
                  <div key={req.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-warning-soft px-2 py-1 text-xs text-warning">
                    <span className="font-semibold">{personName(req.requested_by_person_id)}</span>
                    <span>requested ★ {req.points_spent}</span>
                    <button className="font-semibold underline" onClick={() => onApprove(req.id)}>Approve</button>
                    <button className="font-semibold underline" onClick={() => onReject(req.id)}>Reject</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </td>
      <td className="py-3 pr-3">
        <span className="font-bold text-primary">★ {reward.cost_points}</span>
        <span className="ml-1 text-xs text-muted">{pointsLabel}</span>
      </td>
      <td className="py-3 pr-3">
        {reward.remaining_stock === null ? (
          <span className="text-muted-strong">Unlimited</span>
        ) : (
          <span className={out ? 'font-semibold text-danger' : 'font-semibold text-ink'}>{reward.remaining_stock} left</span>
        )}
      </td>
      <td className="py-3 pr-3">
        <div className="flex flex-wrap gap-1.5">
          {reward.is_archived ? <Badge>Archived</Badge> : reward.is_active ? <Badge className="bg-success-soft text-success">Active</Badge> : <Badge>Hidden</Badge>}
          {out && <Badge className="bg-danger-soft text-danger">Out of stock</Badge>}
        </div>
      </td>
      <td className="py-3 pr-0">
        <div className="flex justify-end gap-1.5">
          <Button size="sm" variant="ghost" onClick={onEdit}>Edit</Button>
          <Button size="sm" variant="ghost" onClick={onToggleActive}>{reward.is_active ? 'Hide' : 'Show'}</Button>
          <Button size="sm" variant="ghost" onClick={onArchive}>{reward.is_archived ? 'Unarchive' : 'Archive'}</Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>Delete</Button>
        </div>
      </td>
    </tr>
  )
}

function RewardEditRow({ reward, onCancel, onSaved, onError }: {
  reward: MeridianReward
  onCancel: () => void
  onSaved: () => void
  onError: () => void
}) {
  return (
    <tr>
      <td colSpan={5} className="py-3">
        <RewardForm reward={reward} onSaved={onSaved} onCancel={onCancel} onError={onError} />
      </td>
    </tr>
  )
}

function RewardForm({ reward, onSaved, onCancel, onError }: {
  reward?: MeridianReward
  onSaved: () => void
  onCancel?: () => void
  onError: () => void
}) {
  const [f, setF] = useState({
    name: reward?.name || '',
    cost_points: String(reward?.cost_points ?? 20),
    description: reward?.description || '',
    image_url: reward?.image_url || '',
    price_estimate: reward?.price_estimate || '',
    store_url: reward?.store_url || '',
    quantity: reward?.quantity === null || reward?.quantity === undefined ? '' : String(reward.quantity),
    daily_limit_per_user: reward?.daily_limit_per_user === null || reward?.daily_limit_per_user === undefined ? '' : String(reward.daily_limit_per_user),
    allow_multiple_in_cart: Boolean(reward?.allow_multiple_in_cart),
    disappear_when_empty: reward?.disappear_when_empty ?? true,
    is_active: reward?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const save = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!f.name.trim()) return
    setSaving(true)
    const payload = {
      name: f.name.trim(),
      cost_points: Number(f.cost_points) || 0,
      description: f.description,
      image_url: f.image_url,
      price_estimate: f.price_estimate,
      store_url: f.store_url,
      quantity: f.quantity === '' ? null : Number(f.quantity),
      daily_limit_per_user: f.daily_limit_per_user === '' ? null : Number(f.daily_limit_per_user),
      allow_multiple_in_cart: f.allow_multiple_in_cart,
      disappear_when_empty: f.disappear_when_empty,
      is_active: f.is_active,
    }
    try {
      if (reward) {
        await api.updateMeridianReward(reward.id, payload)
      } else {
        const created = await api.createMeridianReward({
          name: payload.name,
          cost_points: payload.cost_points,
          description: payload.description,
        })
        await api.updateMeridianReward(created.id, payload)
      }
      onSaved()
    } catch {
      onError()
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="rounded-xl border border-line bg-sunken p-3">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input className={`${inputClass} md:col-span-2`} placeholder="Reward name" value={f.name} onChange={e => set('name', e.target.value)} />
        <input className={inputClass} type="number" min="0" placeholder="Cost" value={f.cost_points} onChange={e => set('cost_points', e.target.value)} />
        <input className={inputClass} type="number" min="0" placeholder="Stock blank = unlimited" value={f.quantity} onChange={e => set('quantity', e.target.value)} />
        <textarea className={`${inputClass} md:col-span-2`} placeholder="Description" value={f.description} onChange={e => set('description', e.target.value)} />
        <input className={inputClass} placeholder="Image URL" value={f.image_url} onChange={e => set('image_url', e.target.value)} />
        <input className={inputClass} placeholder="Store URL" value={f.store_url} onChange={e => set('store_url', e.target.value)} />
        <input className={inputClass} placeholder="Price estimate" value={f.price_estimate} onChange={e => set('price_estimate', e.target.value)} />
        <input className={inputClass} type="number" min="0" placeholder="Daily limit" value={f.daily_limit_per_user} onChange={e => set('daily_limit_per_user', e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.allow_multiple_in_cart} onChange={e => set('allow_multiple_in_cart', e.target.checked)} /> Multiple in cart
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.disappear_when_empty} onChange={e => set('disappear_when_empty', e.target.checked)} /> Hide when empty
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.is_active} onChange={e => set('is_active', e.target.checked)} /> Active
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" type="submit" loading={saving} disabled={!f.name.trim()}>Save reward</Button>
        {onCancel && <Button size="sm" type="button" variant="ghost" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  )
}

function ShopperView({
  rewards,
  balance,
  pointsLabel,
  cart,
  onAdd,
  onRemove,
  onCheckout,
  message,
  error,
}: {
  rewards: MeridianReward[]
  balance: number | null
  pointsLabel: string
  cart: number[]
  onAdd: (reward: MeridianReward) => void
  onRemove: (id: number) => void
  onCheckout: () => void
  message: string | null
  error: string | null
}) {
  const total = cart.reduce((sum, id) => sum + (rewards.find(r => r.id === id)?.cost_points || 0), 0)
  return (
    <div className="flex flex-col gap-4">
      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}
      {message && <div className="rounded-xl border border-success/30 bg-success-soft px-4 py-3 text-sm text-success">{message}</div>}
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          {balance !== null && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Your {pointsLabel}</p>
              <p className="text-2xl font-extrabold text-primary">★ {balance}</p>
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            {cart.length > 0 && <span className="text-sm text-muted-strong">{cart.length} items · ★ {total}</span>}
            {cart.length > 0 && <Button size="sm" onClick={onCheckout}>Request rewards</Button>}
          </div>
        </div>
      </Card>
      {cart.length > 0 && (
        <Card title="Cart">
          <ul className="flex flex-col gap-1.5">
            {cart.map((id, idx) => {
              const r = rewards.find(x => x.id === id)
              return (
                <li key={`${id}-${idx}`} className="flex items-center justify-between text-sm">
                  <span className="text-ink">{r?.name} · ★ {r?.cost_points}</span>
                  <button className="text-muted hover:text-danger" onClick={() => onRemove(id)}>remove</button>
                </li>
              )
            })}
          </ul>
        </Card>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {rewards.map(r => {
          const out = r.remaining_stock !== null && r.remaining_stock <= 0
          const cantAfford = balance !== null && balance < r.cost_points
          return (
            <Card key={r.id}>
              {r.image_url && <img src={r.image_url} alt={r.name} className="-mx-5 -mt-3 mb-3 h-36 w-[calc(100%+2.5rem)] object-cover rounded-t-2xl" />}
              <div className="flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-ink">{r.name}</h3>
                  <span className="text-sm font-bold text-primary whitespace-nowrap">★ {r.cost_points}</span>
                </div>
                {r.description && <p className="text-sm text-muted">{r.description}</p>}
                {r.remaining_stock !== null && <Badge className={out ? 'bg-danger-soft text-danger' : undefined}>{out ? 'Out of stock' : `${r.remaining_stock} left`}</Badge>}
                <Button size="sm" disabled={out || cantAfford} onClick={() => onAdd(r)}>{cantAfford ? 'Not enough' : 'Add to cart'}</Button>
              </div>
            </Card>
          )
        })}
        {rewards.length === 0 && <p className="text-sm text-muted text-center py-8 sm:col-span-2 xl:col-span-3">No rewards available.</p>}
      </div>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-soft">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold text-ink">{value}</p>
      <p className="mt-1 text-sm text-muted">{detail}</p>
    </div>
  )
}

function removeOne(items: number[], id: number) {
  const idx = items.indexOf(id)
  return idx < 0 ? items : [...items.slice(0, idx), ...items.slice(idx + 1)]
}
