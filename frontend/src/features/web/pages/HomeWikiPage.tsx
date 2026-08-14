import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { WikiCategory, WikiPage } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Input, SearchField, Textarea, Select, Field } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { Tabs, type TabDef } from '../../../components/Tabs'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { useAuth } from '../../auth/AuthContext'
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'
import { ColourPicker } from '../../../components/ColourPicker'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const VISIBILITY_OPTS = [
  { value: 'household', label: 'Household' },
  { value: 'private', label: 'Private (only me)' },
  { value: 'sensitive', label: 'Sensitive' },
]

function TagRow({ tags }: { tags: string[] }) {
  if (!tags.length) return null
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {tags.map(t => (
        <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">#{t}</span>
      ))}
    </div>
  )
}

function Flags({ page }: { page: WikiPage }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {page.category_name && (
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ backgroundColor: `${page.category_colour || '#0ca678'}22`, color: page.category_colour || '#0ca678' }}
        >
          {page.category_name}
        </span>
      )}
      {page.is_favourite && <span className="text-xs" title="Favourite">⭐</span>}
      {page.is_emergency && <span className="text-xs px-1.5 py-0.5 rounded-full bg-danger-soft text-danger font-medium">Emergency</span>}
      {page.is_kiosk_safe && <span className="text-xs px-1.5 py-0.5 rounded-full bg-success-soft text-success font-medium">Kiosk</span>}
      {page.visibility === 'private' && <span className="text-xs text-muted">🔒 Private</span>}
      {page.visibility === 'sensitive' && <span className="text-xs text-muted">🔒 Sensitive</span>}
    </div>
  )
}

// ===========================================================================
// Page form (create + edit)
// ===========================================================================

type PageFormState = {
  title: string; body: string; category_id: string; tags: string
  is_favourite: boolean; is_emergency: boolean; is_kiosk_safe: boolean; visibility: string
}

function blankForm(categoryId?: number | null): PageFormState {
  return {
    title: '', body: '', category_id: categoryId ? String(categoryId) : '', tags: '',
    is_favourite: false, is_emergency: false, is_kiosk_safe: false, visibility: 'household',
  }
}

function fromPage(p: WikiPage): PageFormState {
  return {
    title: p.title, body: p.body, category_id: p.category_id ? String(p.category_id) : '',
    tags: p.tags, is_favourite: p.is_favourite, is_emergency: p.is_emergency,
    is_kiosk_safe: p.is_kiosk_safe, visibility: p.visibility,
  }
}

function PageForm({ categories, initial, onSubmit, onCancel, submitting }: {
  categories: WikiCategory[]
  initial: PageFormState
  onSubmit: (data: PageFormState) => void
  onCancel: () => void
  submitting: boolean
}) {
  const [f, setF] = useState(initial)
  const set = <K extends keyof PageFormState>(k: K, v: PageFormState[K]) => setF(prev => ({ ...prev, [k]: v }))

  return (
    <form
      onSubmit={e => { e.preventDefault(); if (f.title.trim()) onSubmit(f) }}
      className="space-y-3 bg-sunken rounded-2xl p-4"
    >
      <Field label="Page title"><Input data-autofocus placeholder="e.g. Wi-Fi or bin night" value={f.title} onChange={e => set('title', e.target.value)} /></Field>
      <Field label="Household information"><Textarea placeholder="Write the details here…" rows={5} value={f.body} onChange={e => set('body', e.target.value)} /></Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="Category">
          <Select value={f.category_id} onChange={e => set('category_id', e.target.value)}>
            <option value="">No category</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Visibility">
          <Select value={f.visibility} onChange={e => set('visibility', e.target.value)}>
            {VISIBILITY_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select>
        </Field>
      </div>
      <Field label="Tags" hint="Separate tags with commas."><Input placeholder="e.g. internet, account" value={f.tags} onChange={e => set('tags', e.target.value)} /></Field>
      <div className="flex flex-wrap gap-4 text-sm text-muted-strong">
        <label className="flex min-h-10 items-center gap-2"><input type="checkbox" checked={f.is_favourite} onChange={e => set('is_favourite', e.target.checked)} /> ⭐ Favourite</label>
        <label className="flex min-h-10 items-center gap-2"><input type="checkbox" checked={f.is_emergency} onChange={e => set('is_emergency', e.target.checked)} /> 🚨 Emergency info</label>
        <label className="flex min-h-10 items-center gap-2"><input type="checkbox" checked={f.is_kiosk_safe} onChange={e => set('is_kiosk_safe', e.target.checked)} /> Kiosk-safe</label>
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={submitting} disabled={!f.title.trim()}>Save page</Button>
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

// docs/36 §6.7: tapping a page reads it full-screen, and Edit is an action on that page rather
// than an inline form replacing the card in the middle of the browse grid.
function PageDetailModal({ page, categories, onChange, onDelete, onError, onClose, canDelete }: {
  page: WikiPage
  categories: WikiCategory[]
  onChange: (p: WikiPage) => void
  onDelete: (id: number) => void
  onError: (m: string) => void
  onClose: () => void
  canDelete: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)

  const save = async (data: PageFormState) => {
    setBusy(true)
    try {
      const updated = await api.updateWikiPage(page.id, {
        title: data.title.trim(), body: data.body, tags: data.tags,
        category_id: data.category_id ? Number(data.category_id) : null,
        is_favourite: data.is_favourite, is_emergency: data.is_emergency,
        is_kiosk_safe: data.is_kiosk_safe, visibility: data.visibility,
      })
      onChange(updated); setEditing(false)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!(await confirmDialog({ title: `Delete "${page.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteWikiPage(page.id); onDelete(page.id); onClose() } catch (e) { onError(errMsg(e)) }
  }
  const toggleFavourite = async () => {
    try { onChange(await api.updateWikiPage(page.id, { is_favourite: !page.is_favourite })) }
    catch (e) { onError(errMsg(e)) }
  }

  return (
    <Modal title={editing ? `Edit "${page.title}"` : page.title} onClose={onClose} size="full">
      {editing ? (
        <PageForm categories={categories} initial={fromPage(page)} onSubmit={save} onCancel={() => setEditing(false)} submitting={busy} />
      ) : (
        <div className="flex flex-col gap-4">
          <Flags page={page} />
          {page.body ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{page.body}</p>
          ) : (
            <p className="text-sm italic text-muted">No details yet — tap Edit to add some.</p>
          )}
          <TagRow tags={page.tag_list} />
          <div className="flex flex-wrap gap-2 border-t border-line pt-3">
            <Button variant="secondary" onClick={toggleFavourite}>{page.is_favourite ? '⭐ Favourited' : '☆ Add to favourites'}</Button>
            <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
            {canDelete && <Button variant="danger" onClick={remove}>Delete</Button>}
          </div>
        </div>
      )}
    </Modal>
  )
}

function PageCard({ page, categories, onChange, onDelete, onError, canDelete, open, onOpen, onClose }: {
  page: WikiPage
  categories: WikiCategory[]
  onChange: (p: WikiPage) => void
  onDelete: (id: number) => void
  onError: (m: string) => void
  canDelete: boolean
  open?: boolean
  onOpen?: () => void
  onClose?: () => void
}) {
  const [localOpen, setLocalOpen] = useState(false)
  const isOpen = open ?? localOpen
  const openPage = onOpen ?? (() => setLocalOpen(true))
  const closePage = onClose ?? (() => setLocalOpen(false))

  const toggleFavourite = async () => {
    try { onChange(await api.updateWikiPage(page.id, { is_favourite: !page.is_favourite })) }
    catch (e) { onError(errMsg(e)) }
  }

  return (
    <>
      <Card className="group">
        <div className="flex items-start justify-between gap-2">
          <button type="button" className="min-h-11 min-w-0 flex-1 text-left" onClick={openPage}>
            <div className="font-semibold text-ink truncate">{page.title}</div>
            <div className="mt-1"><Flags page={page} /></div>
          </button>
          <button type="button" onClick={toggleFavourite} className="grid min-h-11 min-w-11 flex-shrink-0 place-items-center text-muted hover:text-warning" aria-label={page.is_favourite ? `Remove ${page.title} from favourites` : `Add ${page.title} to favourites`}>
            {page.is_favourite ? '⭐' : '☆'}
          </button>
        </div>
      </Card>
      {isOpen && (
        <PageDetailModal
          page={page} categories={categories} canDelete={canDelete}
          onChange={onChange} onDelete={onDelete} onError={onError}
          onClose={closePage}
        />
      )}
    </>
  )
}

// ===========================================================================
// Pages tab
// ===========================================================================

type Filter = 'all' | 'favourites' | 'emergency'

function PagesTab({ categories, isAdmin, onError, openedPageId, onOpenPage, onClosePage }: {
  categories: WikiCategory[]; isAdmin: boolean; onError: (m: string) => void
  openedPageId: number
  onOpenPage: (id: number) => void
  onClosePage: () => void
}) {
  const [pages, setPages] = useState<WikiPage[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Filter>('all')
  const [categoryId, setCategoryId] = useState('')
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)

  const load = () => {
    setLoading(true)
    api.getWikiPages({
      favourites: filter === 'favourites',
      emergency: filter === 'emergency',
      category: categoryId ? Number(categoryId) : undefined,
    }).then(setPages).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }
  useEffect(load, [filter, categoryId])

  const create = async (data: PageFormState) => {
    setBusy(true)
    try {
      await api.createWikiPage({
        title: data.title.trim(), body: data.body, tags: data.tags,
        category_id: data.category_id ? Number(data.category_id) : null,
        is_favourite: data.is_favourite, is_emergency: data.is_emergency,
        is_kiosk_safe: data.is_kiosk_safe, visibility: data.visibility,
      })
      setCreating(false); load()
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'favourites', label: '⭐ Favourites' },
    { key: 'emergency', label: '🚨 Emergency' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-1 rounded-xl bg-sunken p-1">
          {FILTERS.map(fl => (
            <button
              type="button"
              key={fl.key}
              onClick={() => setFilter(fl.key)}
              className={`min-h-11 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${filter === fl.key ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}
            >
              {fl.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Select value={categoryId} onChange={e => setCategoryId(e.target.value)} className="!w-auto">
            <option value="">All categories</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
          {!creating && <Button variant="secondary" onClick={() => setCreating(true)}>+ New page</Button>}
        </div>
      </div>

      {creating && (
        <Modal title="New page" onClose={() => setCreating(false)} size="full">
          <PageForm categories={categories} initial={blankForm(categoryId ? Number(categoryId) : null)} onSubmit={create} onCancel={() => setCreating(false)} submitting={busy} />
        </Modal>
      )}

      {loading ? (
        <Card><p className="text-sm text-muted">Loading…</p></Card>
      ) : pages.length === 0 ? (
        <EmptyState icon="📖" title="No pages yet" hint="Add household knowledge — WiFi, bin night, emergency contacts, how-tos." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {pages.map(p => (
            <PageCard
              key={p.id} page={p} categories={categories} canDelete={isAdmin}
              onChange={u => setPages(prev => prev.map(x => x.id === u.id ? u : x))}
              onDelete={id => setPages(prev => prev.filter(x => x.id !== id))}
              onError={onError}
              open={openedPageId === p.id}
              onOpen={() => onOpenPage(p.id)}
              onClose={onClosePage}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Categories tab
// ===========================================================================

function CategoriesTab({ categories, onChange, isAdmin, onError }: {
  categories: WikiCategory[]
  onChange: (list: WikiCategory[]) => void
  isAdmin: boolean
  onError: (m: string) => void
}) {
  const [name, setName] = useState('')
  const [colour, setColour] = useState('#0ca678')
  const [busy, setBusy] = useState(false)

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      const created = await api.createWikiCategory({ name: name.trim(), colour })
      onChange([...categories, created]); setName('')
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const toggleHidden = async (c: WikiCategory) => {
    try {
      const updated = await api.updateWikiCategory(c.id, { is_hidden: !c.is_hidden })
      onChange(categories.map(x => x.id === c.id ? updated : x))
    } catch (e) { onError(errMsg(e)) }
  }
  const remove = async (c: WikiCategory) => {
    if (!(await confirmDialog({ title: `Delete "${c.name}"?`, message: 'Its pages keep their content but lose the category.', confirmLabel: 'Delete' }))) return
    try { await api.deleteWikiCategory(c.id); onChange(categories.filter(x => x.id !== c.id)) }
    catch (e) { onError(errMsg(e)) }
  }

  return (
    <div className="space-y-4">
      {isAdmin && (
        <Card title="Add category">
          <form onSubmit={add} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_5rem_auto] sm:items-end">
            <Field label="Category name"><Input autoFocus value={name} onChange={e => setName(e.target.value)} /></Field>
            <Field label="Colour"><ColourPicker value={colour} onChange={setColour} ariaLabel="Wiki category colour" /></Field>
            <Button type="submit" loading={busy} disabled={!name.trim()}>Add</Button>
          </form>
        </Card>
      )}

      {categories.length === 0 ? (
        <EmptyState icon="🗂" title="No categories" hint="Categories help organise the wiki." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {categories.map(c => (
            <Card key={c.id} className="group">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="h-3 w-3 rounded-full flex-shrink-0" style={{ backgroundColor: c.colour || '#0ca678' }} />
                  <span className={`font-medium truncate ${c.is_hidden ? 'text-muted line-through' : 'text-ink'}`}>{c.name}</span>
                  <span className="text-xs text-muted flex-shrink-0">{c.page_count ?? 0}</span>
                </div>
                {isAdmin && (
                  <div className="flex flex-shrink-0 gap-1 sm:opacity-0 sm:group-hover:opacity-100 transition">
                    <button type="button" onClick={() => toggleHidden(c)} className="min-h-10 rounded-lg px-2 text-xs font-semibold text-muted hover:bg-sunken hover:text-ink">{c.is_hidden ? 'Show' : 'Hide'}</button>
                    <button type="button" onClick={() => remove(c)} className="min-h-10 rounded-lg px-2 text-xs font-semibold text-muted hover:text-danger">Delete</button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Page
// ===========================================================================

type Tab = 'pages' | 'categories'
const TABS: TabDef<Tab>[] = [
  { key: 'pages', label: 'Pages' },
  { key: 'categories', label: 'Categories' },
]

export function HomeWikiPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'manager'
  const [tab, setTab] = useUrlTab<Tab>('pages', TABS.map(item => item.key))
  const [categories, setCategories] = useState<WikiCategory[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useUrlQueryState()
  const [searchParams, setSearchParams] = useSearchParams()
  const [results, setResults] = useState<WikiPage[] | null>(null)
  const openedPageId = Number(searchParams.get('page') || 0)

  useEffect(() => { api.getWikiCategories(isAdmin).then(setCategories).catch(e => setError(errMsg(e))) }, [isAdmin])

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults(null); return }
    const id = setTimeout(() => { api.searchWiki(q).then(r => setResults(r.pages)).catch(e => setError(errMsg(e))) }, 300)
    return () => clearTimeout(id)
  }, [query])

  const visibleCategories = useMemo(() => categories.filter(c => isAdmin || !c.is_hidden), [categories, isAdmin])
  const openPage = (id: number) => {
    const next = new URLSearchParams(searchParams)
    next.set('page', String(id))
    next.set('tab', 'pages')
    setSearchParams(next)
  }
  const closePage = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('page')
    setSearchParams(next)
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Home Guide" icon="📖" />

      <SearchField value={query} onChange={e => setQuery(e.target.value)} onClear={() => setQuery('')} placeholder="Search the wiki…" />

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {results !== null ? (
        results.length === 0 ? (
          <EmptyState icon="🔍" title="No matches" hint="Try a page title, keyword or tag." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {results.map(p => (
              <PageCard
                key={p.id} page={p} categories={visibleCategories} canDelete={user?.role === 'admin'}
                onChange={u => setResults(prev => prev ? prev.map(x => x.id === u.id ? u : x) : prev)}
                onDelete={id => setResults(prev => prev ? prev.filter(x => x.id !== id) : prev)}
                onError={setError}
                open={openedPageId === p.id}
                onOpen={() => openPage(p.id)}
                onClose={closePage}
              />
            ))}
          </div>
        )
      ) : (
        <>
          <Tabs tabs={TABS} active={tab} onChange={setTab} />
          {tab === 'pages' && <PagesTab categories={visibleCategories} isAdmin={user?.role === 'admin'} onError={setError} openedPageId={openedPageId} onOpenPage={openPage} onClosePage={closePage} />}
          {tab === 'categories' && <CategoriesTab categories={categories} onChange={setCategories} isAdmin={isAdmin} onError={setError} />}
        </>
      )}
    </div>
  )
}
