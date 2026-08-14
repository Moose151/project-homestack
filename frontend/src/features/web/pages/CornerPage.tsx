import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { CornerActivity, CornerCollection, CornerResponse, LinkPreview, Person } from '../../../api/types'
import { Avatar } from '../../../components/Avatar'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select } from '../../../components/Field'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'
import { Tabs } from '../../../components/Tabs'
import { useAuth } from '../../auth/AuthContext'
import { useUrlTab } from '../../../hooks/useUrlTab'
import { MobileListRow } from '../../../components/mobile'

const TABS = ['overview', 'activity', 'assigned', 'lists'] as const
type CornerTab = typeof TABS[number]
type ListSection = 'personal' | 'rooms' | 'meridian'
const REACTIONS = ['❤️', '👍', '🎉', '💪', '👏']

const sourceNames: Record<string, string> = {
  atlas: 'Lists & Notes', fitness: 'Fitness', meridian: 'Tasks', travel: 'Travel',
  education: 'Education', homestead: 'Home',
}

function when(value: string | null) {
  if (!value) return 'No date set'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function ActivityCard({ row, reacting, onReact }: {
  row: CornerActivity
  reacting: string
  onReact: (emoji: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const groups = new Map(row.reactions.map(group => [group.emoji, group]))
  const setSummary = (exercise: NonNullable<CornerActivity['detail_summary']>['exercises'][number]) => exercise.sets.map(set => {
    if (set.weight && set.reps) return `${Number(set.weight)} ${exercise.weight_unit} × ${set.reps}`
    if (set.reps) return `${set.reps} reps`
    if (Number(set.distance)) return `${Number(set.distance)} ${exercise.distance_unit}${set.duration_seconds ? ` · ${Math.round(set.duration_seconds / 60)} min` : ''}`
    if (set.duration_seconds) return `${Math.round(set.duration_seconds / 60)} min`
    return ''
  }).filter(Boolean).join(' · ')
  return (
    <article className="rounded-2xl border border-line bg-surface p-4 shadow-soft">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl bg-primary-soft text-lg">
          {row.kind === 'completed' ? '✓' : row.source_node === 'fitness' ? '🏋️' : '✦'}
        </span>
        <div className="min-w-0 flex-1">
          <Link to={row.action_url} className="font-bold text-ink hover:text-primary">{row.title}</Link>
          <p className="mt-0.5 text-xs text-muted">{row.summary} · {when(row.occurred_at)}</p>
          <div className="mt-2 flex flex-wrap gap-3 text-xs font-bold text-primary"><Link to={row.action_url}>Open →</Link>{row.detail_summary && <button type="button" onClick={() => setExpanded(value => !value)}>{expanded ? 'Hide details' : 'Show details'}</button>}</div>
          {expanded && row.detail_summary && <div className="mt-3 space-y-2 rounded-xl bg-sunken p-3"><p className="text-xs font-bold text-muted-strong">{Math.round((row.detail_summary.duration_seconds || 0) / 60)} min · {row.detail_summary.total_reps} reps · {Number(row.detail_summary.total_volume).toLocaleString()} kg volume</p>{row.detail_summary.exercises.map((exercise, index) => <div key={`${exercise.name}-${index}`}><p className="text-sm font-bold text-ink">{exercise.name}</p><p className="text-xs text-muted">{setSummary(exercise) || 'No completed sets'}</p></div>)}</div>}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {REACTIONS.map(emoji => {
              const group = groups.get(emoji)
              return (
                <button
                  key={emoji}
                  disabled={reacting === row.key}
                  onClick={() => onReact(emoji)}
                  title={group?.people.map(person => person.name).join(', ') || `React ${emoji}`}
                  className={`min-h-9 rounded-full border px-2.5 text-sm transition-all ${group?.mine ? 'border-primary bg-primary-soft' : 'border-line bg-sunken hover:border-primary/50'} disabled:opacity-50`}
                >
                  {emoji}{group?.count ? <span className="ml-1 text-xs font-bold text-muted-strong">{group.count}</span> : null}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </article>
  )
}

function ProductEntry({ list, isMine, personName, onSaved }: {
  list: CornerCollection
  isMine: boolean
  personName: string
  onSaved: () => Promise<void>
}) {
  const [url, setUrl] = useState('')
  const [preview, setPreview] = useState<LinkPreview | null>(null)
  const [title, setTitle] = useState('')
  const [price, setPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const inspect = async () => {
    if (!url.trim()) return
    setBusy(true); setError(null)
    try {
      const result = await api.previewProductLink(url.trim())
      setPreview(result)
      setTitle(current => current.trim() ? current : result.title)
      setPrice(current => current || result.price || '')
    } catch (reason) {
      setPreview(null)
      setError(`${reason instanceof Error ? reason.message : 'This shop could not be read.'} You can still enter the item manually.`)
    } finally { setBusy(false) }
  }

  const save = async () => {
    if (!list.list_id || !title.trim()) return
    setBusy(true); setError(null)
    const data = {
      title: title.trim(), product_url: preview?.source_url || url.trim(),
      source_image_url: preview?.image_url || '', retailer: preview?.retailer || '',
      unit_price: price || null, currency: preview?.currency || 'AUD',
      cache_image: true, price_watch_enabled: isMine && list.kind === 'wishlist',
    }
    try {
      if (isMine) await api.createItem(list.list_id, data)
      else await api.suggestListItem(list.list_id, data)
      setUrl(''); setPreview(null); setTitle(''); setPrice('')
      await onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The item could not be saved.')
    } finally { setBusy(false) }
  }

  return (
    <div className="mt-4 rounded-2xl border border-dashed border-line-strong bg-sunken/60 p-3">
      <p className="mb-2 text-xs font-bold text-muted-strong">{isMine ? 'Add an item' : `Suggest something for ${personName}`}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input value={url} onChange={event => setUrl(event.target.value)} placeholder="Paste a product URL" type="url" />
        <Button variant="secondary" onClick={inspect} disabled={busy || !url.trim()}>{busy ? 'Checking…' : 'Fill from link'}</Button>
      </div>
      {error && <div className="mt-2"><InlineAlert message={error} onDismiss={() => setError(null)} /></div>}
      {(preview || error) && (
        <div className="mt-3 grid gap-3 sm:grid-cols-[72px_1fr_120px]">
          <div className="h-[72px] overflow-hidden rounded-xl border border-line bg-surface">
            {preview?.image_url ? <img src={preview.image_url} alt="" className="h-full w-full object-cover" /> : <span className="grid h-full place-items-center text-xl text-muted">🛍</span>}
          </div>
          <Field label="Item name"><Input value={title} onChange={event => setTitle(event.target.value)} /></Field>
          <Field label="Price"><Input value={price} onChange={event => setPrice(event.target.value)} inputMode="decimal" placeholder="0.00" /></Field>
          {preview?.warnings.length ? <p className="text-xs text-muted sm:col-start-2 sm:col-span-2">{preview.warnings.join(' ')}</p> : null}
          <div className="sm:col-start-2 sm:col-span-2"><Button onClick={save} disabled={busy || !title.trim()}>{isMine ? 'Add to list' : 'Send suggestion'}</Button></div>
        </div>
      )}
    </div>
  )
}

function CollectionCard({ list, corner, reload }: { list: CornerCollection; corner: CornerResponse; reload: () => Promise<void> }) {
  const [reviewing, setReviewing] = useState<number | null>(null)
  const review = async (suggestionId: number, action: 'accept' | 'dismiss') => {
    if (!list.list_id) return
    setReviewing(suggestionId)
    try { await api.reviewListSuggestion(list.list_id, suggestionId, action); await reload() }
    finally { setReviewing(null) }
  }
  return (
    <Card className="overflow-hidden">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-extrabold text-ink">{list.title}</h3>
            <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-bold uppercase text-primary">{list.kind === 'wishlist' ? 'Wish list' : list.kind}</span>
            {list.visibility === 'private' && <span className="text-xs text-muted">🔒 Private</span>}
          </div>
          <p className="mt-1 text-xs text-muted">{list.summary}</p>
        </div>
        <Link className="text-xs font-bold text-primary hover:underline" to={list.action_url}>Open</Link>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {list.items?.map(item => (
          <div key={item.id} className="flex min-w-0 gap-3 rounded-xl border border-line bg-sunken/45 p-2.5">
            <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded-lg bg-surface">
              {item.cached_image_url || item.source_image_url
                ? <img src={item.cached_image_url || item.source_image_url} alt="" className="h-full w-full object-cover" />
                : <span className="grid h-full place-items-center text-lg">🛍</span>}
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm font-bold text-ink">{item.title}</p>
              <p className="mt-0.5 truncate text-xs text-muted">{item.retailer || 'Personal item'}{item.unit_price ? ` · $${item.unit_price}` : ''}</p>
              {item.price_watch?.is_active && <p className="mt-1 text-[10px] font-bold text-success">Price watch on</p>}
            </div>
          </div>
        ))}
      </div>
      {!list.items?.length && <p className="mt-3 text-xs text-muted">Nothing has been added yet.</p>}
      {corner.person.is_me && Boolean(list.suggestions?.length) && (
        <div className="mt-4 rounded-2xl border border-primary/25 bg-primary-soft/35 p-3">
          <p className="text-xs font-extrabold uppercase tracking-wide text-primary">Suggestions to review</p>
          <div className="mt-2 space-y-2">
            {list.suggestions?.map(suggestion => (
              <div key={suggestion.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-surface p-2.5">
                <div className="min-w-0 flex-1"><p className="text-sm font-bold text-ink">{suggestion.title}</p><p className="text-xs text-muted">Suggested by {suggestion.suggested_by_name}{suggestion.unit_price ? ` · $${suggestion.unit_price}` : ''}</p></div>
                <Button size="sm" onClick={() => review(suggestion.id, 'accept')} disabled={reviewing === suggestion.id}>Accept</Button>
                <Button size="sm" variant="ghost" onClick={() => review(suggestion.id, 'dismiss')} disabled={reviewing === suggestion.id}>Dismiss</Button>
              </div>
            ))}
          </div>
        </div>
      )}
      {list.list_id && <ProductEntry list={list} isMine={corner.person.is_me} personName={corner.person.name} onSaved={reload} />}
    </Card>
  )
}

export function CornerPage() {
  const { personId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [tab, setTab] = useUrlTab<CornerTab>('overview', TABS)
  const [people, setPeople] = useState<Person[]>([])
  const [peopleLoaded, setPeopleLoaded] = useState(false)
  const [corner, setCorner] = useState<CornerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reacting, setReacting] = useState('')
  const [newListName, setNewListName] = useState('')
  const [newListType, setNewListType] = useState<'wishlist' | 'shopping'>('wishlist')
  const [newListVisibility, setNewListVisibility] = useState<'household' | 'private'>('household')
  const [listSection, setListSection] = useState<ListSection>('personal')
  const selectedId = Number(personId) || null

  useEffect(() => {
    api.getPeople().then(rows => {
      setPeople(rows)
      if (!selectedId) {
        const mine = rows.find(person => person.linked_user_id === user?.id)
        if (mine) navigate(`/corners/${mine.id}`, { replace: true })
      }
    }).catch(reason => setError(reason instanceof Error ? reason.message : 'People could not be loaded.')).finally(() => setPeopleLoaded(true))
  }, [navigate, selectedId, user?.id])

  const load = useCallback(async () => {
    if (!selectedId) return
    setLoading(true); setError(null)
    try { setCorner(await api.getCorner(selectedId)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'This Corner could not be loaded.') }
    finally { setLoading(false) }
  }, [selectedId])
  useEffect(() => { load() }, [load])

  // A single `?.` before `.collections` only short-circuits while `corner` itself is nullish; if
  // `corner` ever resolves truthy with `collections` missing (a malformed response), `.filter()`
  // still throws — and with no error boundary, that takes the whole app down, not just this page.
  const personalCollections = useMemo(() => corner?.collections?.filter(row => row.source_node === 'atlas') ?? [], [corner])
  const roomCollections = useMemo(() => corner?.collections?.filter(row => row.source_node === 'homestead') ?? [], [corner])
  const meridianCollections = useMemo(() => corner?.collections?.filter(row => row.source_node === 'meridian') ?? [], [corner])
  const react = async (row: CornerActivity, emoji: string) => {
    if (!corner) return
    setReacting(row.key)
    try { setCorner((await api.toggleCornerReaction(corner.person.id, row.key, emoji)).corner) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The reaction could not be saved.') }
    finally { setReacting('') }
  }
  const createPersonalList = async () => {
    if (!corner || !newListName.trim()) return
    try {
      await api.createList({ title: newListName.trim(), list_type: newListType, visibility: newListVisibility, owner_person: corner.person.id })
      setNewListName(''); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The list could not be created.') }
  }

  if (!selectedId && peopleLoaded) return <EmptyState icon="✨" title="Your Corner is not linked yet" hint="Ask a HomeStack administrator to link this login to your household profile. You can still open another member’s Corner from their avatar elsewhere in HomeStack." />
  if (!selectedId || loading) return <PageSkeleton cards={4} />
  if (!corner) return <InlineAlert message={error || 'This Corner is unavailable.'} onRetry={load} />
  const pageTitle = corner.person.is_me ? 'My Corner' : `${corner.person.name}’s Corner`

  return (
    <div className="space-y-5">
      {error && <InlineAlert message={error} onDismiss={() => setError(null)} />}
      <section className="overflow-hidden rounded-3xl border border-line bg-surface shadow-soft">
        <div className="h-20 sm:h-24" style={{ background: `linear-gradient(120deg, ${corner.person.colour || '#1d7a91'}35, var(--hs-primary-soft), transparent)` }} />
        <div className="px-4 pb-4 sm:px-6">
          <div className="-mt-8 flex flex-wrap items-end gap-3">
            <div className="rounded-full border-4 border-surface bg-surface"><Avatar name={corner.person.name} colour={corner.person.colour} avatar={corner.person.avatar} size="lg" /></div>
            <div className="min-w-0 flex-1 pb-1">
              <h1 className="text-2xl font-black tracking-tight text-ink">{pageTitle}</h1>
              <p className="text-xs text-muted">What’s happening, what’s assigned, and the things they’re planning.</p>
            </div>
          </div>
          <div className="mt-4 max-w-sm">
            <Field label="View Corner">
              <Select
                aria-label="Choose a Corner"
                value={corner.person.id}
                onChange={event => navigate(`/corners/${event.target.value}?tab=${tab}`)}
              >
                {people.map(person => (
                  <option key={person.id} value={person.id}>
                    {person.linked_user_id === user?.id ? 'My Corner' : `${person.preferred_name || person.display_name}’s Corner`}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </div>
      </section>

      <Tabs active={tab} onChange={setTab} tabs={[
        { key: 'overview', label: 'Overview' },
        { key: 'activity', label: 'Activity', badge: corner.summary.activity_count },
        { key: 'assigned', label: 'Assigned', badge: corner.summary.assignment_count },
        { key: 'lists', label: 'Lists & wishes', badge: corner.summary.collection_count },
      ]} mobileSelectLabel="Corner section" />

      {tab === 'overview' && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="Recent activity" className="lg:col-span-2">
            <div className="space-y-2">{corner.activity.slice(0, 4).map(row => <ActivityCard key={row.key} row={row} reacting={reacting} onReact={emoji => react(row, emoji)} />)}</div>
            {!corner.activity.length && <EmptyState icon="✨" title="No recent activity" hint="Completed workouts, tasks and plans will appear here." />}
          </Card>
          <div className="space-y-2">
            <MobileListRow
              icon="✓"
              title="Assigned"
              subtitle="Open things across HomeStack"
              trailing={corner.summary.assignment_count || undefined}
              onClick={() => setTab('assigned')}
            />
            <MobileListRow
              icon="🛍"
              title="Lists & wishes"
              subtitle="Personal lists, room plans and wishes"
              trailing={corner.summary.collection_count || undefined}
              onClick={() => setTab('lists')}
            />
            <MobileListRow
              icon="✨"
              title="Activity"
              subtitle="Everything completed recently"
              trailing={corner.summary.activity_count || undefined}
              onClick={() => setTab('activity')}
            />
          </div>
        </div>
      )}

      {tab === 'activity' && <div className="space-y-3">{corner.activity.map(row => <ActivityCard key={row.key} row={row} reacting={reacting} onReact={emoji => react(row, emoji)} />)}{!corner.activity.length && <EmptyState icon="✨" title="No activity in the last 30 days" />}</div>}

      {tab === 'assigned' && (
        <div className="grid gap-3 sm:grid-cols-2">
          {corner.assignments.map(row => <Link key={row.key} to={row.action_url} className="rounded-2xl border border-line bg-surface p-4 shadow-soft hover:border-primary/40"><p className="text-xs font-bold uppercase text-primary">{sourceNames[row.source_node] || row.source_node}</p><h3 className="mt-1 font-extrabold text-ink">{row.title}</h3><p className="mt-1 text-xs text-muted">{row.summary}{row.due_at ? ` · ${when(row.due_at)}` : ''}</p></Link>)}
          {!corner.assignments.length && <EmptyState className="sm:col-span-2" icon="✓" title="Nothing is waiting" hint="Assignments from tasks, fitness, study and room plans will gather here." />}
        </div>
      )}

      {tab === 'lists' && (
        <div className="space-y-4">
          <Tabs variant="secondary" active={listSection} onChange={setListSection} tabs={[
            { key: 'personal', label: 'Personal', badge: personalCollections.length },
            { key: 'rooms', label: 'Room plans', badge: roomCollections.length },
            { key: 'meridian', label: 'Meridian wishes', badge: meridianCollections.length },
          ]} />
          {listSection === 'personal' && corner.person.is_me && (
            <Card title="Start a personal list">
              <div className="grid gap-3 sm:grid-cols-[1fr_150px_150px_auto] sm:items-end">
                <Field label="List name"><Input value={newListName} onChange={event => setNewListName(event.target.value)} placeholder="Things for my room" /></Field>
                <Field label="Type"><Select value={newListType} onChange={event => setNewListType(event.target.value as 'wishlist' | 'shopping')}><option value="wishlist">Wish list</option><option value="shopping">Shopping list</option></Select></Field>
                <Field label="Who can see it"><Select value={newListVisibility} onChange={event => setNewListVisibility(event.target.value as 'household' | 'private')}><option value="household">Household</option><option value="private">Only me</option></Select></Field>
                <Button onClick={createPersonalList} disabled={!newListName.trim()}>Create list</Button>
              </div>
            </Card>
          )}
          {listSection === 'personal' && personalCollections.map(list => <CollectionCard key={list.key} list={list} corner={corner} reload={load} />)}
          {listSection === 'personal' && !personalCollections.length && <EmptyState icon="🛍" title={corner.person.is_me ? 'Create your first personal list' : `${corner.person.name} has no shared lists yet`} hint="Wish lists can watch prices automatically; shopping lists work like normal household lists." />}
          {listSection === 'rooms' && roomCollections.map(row => <Link key={row.key} to={row.action_url} className="block rounded-2xl border border-line bg-surface p-4 shadow-soft hover:border-primary/40"><p className="text-xs font-extrabold uppercase tracking-wide text-primary">Room plan</p><h3 className="mt-1 font-extrabold text-ink">{row.title}</h3><p className="mt-1 text-xs text-muted">{row.summary}</p></Link>)}
          {listSection === 'rooms' && !roomCollections.length && <EmptyState icon="🏠" title="No assigned room-plan items" hint="Products from room plans assigned to this person will appear here." />}
          {listSection === 'meridian' && meridianCollections.map(row => <Link key={row.key} to={row.action_url} className="block rounded-2xl border border-line bg-surface p-4 shadow-soft hover:border-primary/40"><p className="text-xs font-extrabold uppercase tracking-wide text-primary">Points wish</p><h3 className="mt-1 font-extrabold text-ink">{row.title}</h3><p className="mt-1 text-xs text-muted">{row.summary}</p></Link>)}
          {listSection === 'meridian' && !meridianCollections.length && <EmptyState icon="⭐" title="No Meridian wishes" hint="Children’s points-based wishes remain owned by Meridian and appear here when available." />}
        </div>
      )}
    </div>
  )
}
