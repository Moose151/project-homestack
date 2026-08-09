import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../../api/client'
import type {
  Book, BookClub, BookShelfStatus, BooksUser, ClubBookEntry, ClubQueueItem, PersonalBookEntry,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, fieldClass, SearchField } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { Tabs } from '../../../components/Tabs'
import { useUrlAction, useUrlQueryState } from '../../../hooks/useUrlTab'

type Surface = 'personal' | 'club'

const inputCls = fieldClass
// Native selects need right padding so the dropdown arrow doesn't clip the label.
const selectCls = `${fieldClass} pr-9 cursor-pointer`
const shelfLabels: Record<BookShelfStatus, string> = { backlog: 'Backlog', reading: 'Reading', history: 'Read' }
const statuses: BookShelfStatus[] = ['backlog', 'reading', 'history']
const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

function sorted<T extends { position: number; created_at: string }>(items: T[]) {
  return [...items].sort((a, b) => a.position - b.position || a.created_at.localeCompare(b.created_at))
}

function BookLine({ title, author, genre, pages }: { title: string; author?: string; genre?: string; pages?: number | null }) {
  return (
    <div className="min-w-0">
      <p className="font-semibold text-ink truncate">{title}</p>
      <p className="text-xs text-muted truncate">
        {[author, genre, pages ? `${pages} pages` : ''].filter(Boolean).join(' · ') || 'No details yet'}
      </p>
    </div>
  )
}

function TabButton({ active, children, onClick, colour }: {
  active: boolean
  children: React.ReactNode
  onClick: () => void
  colour?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-2 rounded-xl text-sm font-semibold transition-colors ${active ? 'text-white' : 'bg-sunken text-muted-strong hover:text-ink'}`}
      style={active ? { background: colour || 'var(--hs-primary)' } : undefined}
    >
      {children}
    </button>
  )
}

function RatingEditor({ bookId, rating, notes, onSaved }: {
  bookId: number
  rating: number | null
  notes: string
  onSaved: () => void
}) {
  const [value, setValue] = useState<number | ''>(rating ?? '')
  const [text, setText] = useState(notes || '')
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setValue(rating ?? '')
    setText(notes || '')
  }, [rating, notes])

  const save = async () => {
    setBusy(true); setError(null)
    try {
      await api.upsertBookRating({
        book_id: bookId,
        rating: value === '' ? null : Number(value),
        notes: text,
      })
      setOpen(false)
      onSaved()
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      <button type="button" onClick={() => setOpen(v => !v)} className="text-xs font-semibold text-primary hover:underline">
        {rating == null ? 'Rate / notes' : `${rating}/10 · notes`}
      </button>
      {open && (
        <div className="grid gap-2 bg-sunken rounded-xl p-2">
          {error && <p className="text-xs text-danger">{error}</p>}
          <Field label="Rating out of 10">
            <input
              type="number"
              min={0}
              max={10}
              inputMode="numeric"
              className={`${inputCls} max-w-[8rem]`}
              value={value}
              onChange={e => setValue(e.target.value === '' ? '' : Number(e.target.value))}
            />
          </Field>
          <Field label="Your notes">
            <textarea
              className={`${inputCls} min-h-[72px] resize-none`}
              placeholder="What did you think?"
              value={text}
              onChange={e => setText(e.target.value)}
            />
          </Field>
          <Button type="button" size="sm" loading={busy} onClick={save} className="justify-self-start">Save rating</Button>
        </div>
      )}
    </div>
  )
}

function EditBookPanel({ book, onCancel, onSaved }: {
  book: Book
  onCancel: () => void
  onSaved: () => Promise<void>
}) {
  const [title, setTitle] = useState(book.title)
  const [author, setAuthor] = useState(book.author)
  const [pages, setPages] = useState(book.pages?.toString() || '')
  const [genre, setGenre] = useState(book.genre)
  const [isbn, setIsbn] = useState(book.isbn)
  const [description, setDescription] = useState(book.description)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(book.title)
    setAuthor(book.author)
    setPages(book.pages?.toString() || '')
    setGenre(book.genre)
    setIsbn(book.isbn)
    setDescription(book.description)
  }, [book.id, book.title, book.author, book.pages, book.genre, book.isbn, book.description])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true); setError(null)
    try {
      await api.updateBook(book.id, {
        title: title.trim(),
        author: author.trim(),
        pages: pages ? Number(pages) : null,
        genre: genre.trim(),
        isbn: isbn.trim(),
        description: description.trim(),
      })
      await onSaved()
      onCancel()
    } catch (e2) {
      setError(errMsg(e2))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-xl bg-sunken p-2">
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="grid sm:grid-cols-2 gap-2">
        <Field label="Title"><input className={inputCls} value={title} onChange={e => setTitle(e.target.value)} /></Field>
        <Field label="Author"><input className={inputCls} value={author} onChange={e => setAuthor(e.target.value)} /></Field>
        <Field label="Pages"><input className={inputCls} type="number" min={1} inputMode="numeric" value={pages} onChange={e => setPages(e.target.value)} /></Field>
        <Field label="Genre"><input className={inputCls} value={genre} onChange={e => setGenre(e.target.value)} /></Field>
      </div>
      <Field label="ISBN"><input className={inputCls} value={isbn} onChange={e => setIsbn(e.target.value)} /></Field>
      <Field label="Description"><textarea className={`${inputCls} min-h-[72px] resize-none`} value={description} onChange={e => setDescription(e.target.value)} /></Field>
      <div className="flex flex-wrap gap-2 justify-end">
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button type="submit" size="sm" loading={busy} disabled={!title.trim()}>Save book</Button>
      </div>
    </form>
  )
}

function AddBookPanel({ mode, clubs, selectedClub, defaultStatus, onClose, onAdded }: {
  mode: Surface
  clubs: BookClub[]
  selectedClub: BookClub | null
  defaultStatus: BookShelfStatus
  onClose: () => void
  onAdded: () => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [pages, setPages] = useState('')
  const [genre, setGenre] = useState('')
  const [status, setStatus] = useState<BookShelfStatus>(defaultStatus)
  const [clubId, setClubId] = useState<number | ''>(selectedClub?.id || clubs[0]?.id || '')
  const [busy, setBusy] = useState(false)
  const [matches, setMatches] = useState<Book[]>([])
  const [picked, setPicked] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setStatus(defaultStatus), [defaultStatus])
  useEffect(() => setClubId(selectedClub?.id || clubs[0]?.id || ''), [selectedClub?.id, clubs.length])

  // Suggest existing books as the title is typed, to avoid creating duplicate records.
  useEffect(() => {
    const q = title.trim()
    if (picked || q.length < 2) { setMatches([]); return }
    const id = setTimeout(() => { api.searchBooks(q).then(setMatches).catch(() => {}) }, 300)
    return () => clearTimeout(id)
  }, [title, picked])

  const useExisting = (b: Book) => {
    setTitle(b.title); setAuthor(b.author); setPages(b.pages?.toString() || ''); setGenre(b.genre)
    setPicked(true); setMatches([])
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true); setError(null)
    try {
      const book = {
        title: title.trim(),
        author: author.trim(),
        pages: pages ? Number(pages) : null,
        genre: genre.trim(),
      }
      if (mode === 'club') {
        if (!clubId) return
        await api.createClubBook(Number(clubId), { book, status, position: 0 })
      } else {
        await api.createPersonalBook({ book, status, position: 0 })
      }
      setTitle('')
      setAuthor('')
      setPages('')
      setGenre('')
      setPicked(false)
      setMatches([])
      await onAdded()
      onClose()
    } catch (e2) {
      setError(errMsg(e2))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title={mode === 'club' ? 'Add a book to this club' : 'Add a book to your shelves'}>
      <form onSubmit={submit} className="space-y-3">
        {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <div className="grid md:grid-cols-[1.3fr_1fr_7rem_1fr] gap-2">
          <Field label="Title"><input autoFocus className={inputCls} value={title} onChange={e => { setTitle(e.target.value); setPicked(false) }} placeholder="Start typing to find an existing book" /></Field>
          <Field label="Author"><input className={inputCls} value={author} onChange={e => setAuthor(e.target.value)} /></Field>
          <Field label="Pages"><input className={inputCls} type="number" min={1} inputMode="numeric" value={pages} onChange={e => setPages(e.target.value)} /></Field>
          <Field label="Genre"><input className={inputCls} value={genre} onChange={e => setGenre(e.target.value)} /></Field>
        </div>
        {matches.length > 0 && (
          <div className="rounded-xl border border-line bg-surface p-2 text-sm">
            <p className="px-1 pb-1 text-xs text-muted">Already in your library — reuse instead of adding a duplicate:</p>
            {matches.slice(0, 4).map(b => (
              <button key={b.id} type="button" onClick={() => useExisting(b)}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-sunken">
                <span className="font-medium text-ink">{b.title}</span>
                {b.author && <span className="text-xs text-muted">· {b.author}</span>}
              </button>
            ))}
          </div>
        )}
        <div className="grid md:grid-cols-[1fr_1fr_auto_auto] gap-2 items-center">
          <Field label="Shelf">
            <select className={selectCls} value={status} onChange={e => setStatus(e.target.value as BookShelfStatus)}>
              {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
            </select>
          </Field>
          {mode === 'club' && (
            <Field label="Book club">
              <select className={selectCls} value={clubId} onChange={e => setClubId(Number(e.target.value))}>
                {clubs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
          )}
          <Button type="submit" className="md:self-end" loading={busy} disabled={!title.trim() || (mode === 'club' && !clubId)}>Add book</Button>
          <Button type="button" className="md:self-end" variant="ghost" onClick={onClose}>Cancel</Button>
        </div>
      </form>
    </Card>
  )
}

function PersonalBookCard({ entry, clubs, onRefresh, onMove, onDelete, onAddToClub }: {
  entry: PersonalBookEntry
  clubs: BookClub[]
  onRefresh: () => Promise<void>
  onMove: (status: BookShelfStatus) => Promise<void>
  onDelete: () => Promise<void>
  onAddToClub: (clubId: number) => Promise<void>
}) {
  const [clubId, setClubId] = useState<number | ''>(clubs[0]?.id || '')
  const [editing, setEditing] = useState(false)

  useEffect(() => setClubId(clubs[0]?.id || ''), [clubs.length])

  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-3">
      <div className="flex items-start gap-2">
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <div className="ml-auto flex items-center gap-1">
          <button type="button" onClick={() => setEditing(v => !v)} className="min-h-10 px-2 text-xs font-semibold text-muted hover:text-primary" aria-label={`Edit ${entry.book.title}`}>Edit</button>
          <button type="button" onClick={onDelete} className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger" aria-label={`Remove ${entry.book.title}`}>×</button>
        </div>
      </div>
      {editing && <EditBookPanel book={entry.book} onCancel={() => setEditing(false)} onSaved={onRefresh} />}
      <div className="space-y-2">
        <select aria-label={`Shelf for ${entry.book.title}`} className={selectCls} value={entry.status} onChange={e => onMove(e.target.value as BookShelfStatus)}>
          {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
        </select>
        {entry.status === 'backlog' && clubs.length > 0 && (
          <div className="flex gap-2">
            <select aria-label={`Book club for ${entry.book.title}`} className={selectCls} value={clubId} onChange={e => setClubId(Number(e.target.value))}>
              {clubs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <Button type="button" size="sm" variant="secondary" className="flex-shrink-0 whitespace-nowrap" disabled={!clubId} onClick={() => onAddToClub(Number(clubId))}>
              Add to club
            </Button>
          </div>
        )}
      </div>
      <RatingEditor bookId={entry.book_id} rating={entry.rating} notes={entry.notes} onSaved={onRefresh} />
    </div>
  )
}

function ClubBookCard({ entry, club, onRefresh, onMove, onDelete, onQueue }: {
  entry: ClubBookEntry
  club: BookClub
  onRefresh: () => Promise<void>
  onMove: (status: BookShelfStatus) => Promise<void>
  onDelete: () => Promise<void>
  onQueue: () => Promise<void>
}) {
  const [editing, setEditing] = useState(false)

  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-3" style={{ borderLeftColor: entry.added_by_colour || club.colour, borderLeftWidth: 4 }}>
      <div className="flex items-start gap-2">
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <div className="ml-auto flex items-center gap-1">
          <button type="button" onClick={() => setEditing(v => !v)} className="min-h-10 px-2 text-xs font-semibold text-muted hover:text-primary" aria-label={`Edit ${entry.book.title}`}>Edit</button>
          <button type="button" onClick={onDelete} className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger" aria-label={`Remove ${entry.book.title}`}>×</button>
        </div>
      </div>
      {editing && <EditBookPanel book={entry.book} onCancel={() => setEditing(false)} onSaved={onRefresh} />}
      <div className="flex items-center gap-2">
        <select aria-label={`Club shelf for ${entry.book.title}`} className={selectCls} value={entry.status} onChange={e => onMove(e.target.value as BookShelfStatus)}>
          {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
        </select>
        {entry.status === 'backlog' && (
          <Button type="button" size="sm" variant="secondary" className="flex-shrink-0 whitespace-nowrap" onClick={onQueue}>Add up next</Button>
        )}
      </div>
      {entry.status === 'history' && (
        <div className="text-xs text-muted">
          Club average: <span className="font-semibold text-ink">{entry.average_rating == null ? 'none' : `${entry.average_rating.toFixed(1)}/10`}</span>
          {entry.ratings.length > 0 && (
            <span className="block mt-1">{entry.ratings.map(r => `${r.user_name}: ${r.rating ?? '-'}/10`).join(' · ')}</span>
          )}
        </div>
      )}
      <RatingEditor
        bookId={entry.book_id}
        rating={entry.my_rating}
        notes={entry.ratings.find(r => r.book_id === entry.book_id && r.rating === entry.my_rating)?.notes || ''}
        onSaved={onRefresh}
      />
    </div>
  )
}

function ClubSettings({ club, users, onChanged }: {
  club: BookClub
  users: BooksUser[]
  onChanged: () => Promise<void>
}) {
  const [name, setName] = useState(club.name)
  const [colour, setColour] = useState(club.colour)
  const [memberId, setMemberId] = useState<number | ''>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setName(club.name)
    setColour(club.colour)
  }, [club.id, club.name, club.colour])

  const memberIds = new Set(club.memberships.map(m => m.user_id))
  const availableUsers = users.filter(u => !memberIds.has(u.id))

  const act = async (work: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await work()
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 rounded-xl bg-sunken p-3">
      {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
      <div className="grid sm:grid-cols-[minmax(0,1fr)_5rem_auto] gap-2 items-end">
        <Field label="Club name">
          <input className={inputCls} value={name} onChange={e => setName(e.target.value)} />
        </Field>
        <Field label="Colour">
          <input type="color" value={colour} onChange={e => setColour(e.target.value)} className="w-full h-11 rounded-xl border border-line p-1 bg-surface" />
        </Field>
        <Button type="button" variant="secondary" loading={busy} disabled={!name.trim()} onClick={() => act(async () => { await api.updateBookClub(club.id, { name: name.trim(), colour }); await onChanged() })}>
          Save club
        </Button>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {club.memberships.map(m => (
          <span key={m.id} className="inline-flex min-h-10 items-center gap-1.5 rounded-full bg-surface pl-3 pr-1 text-xs text-muted-strong">
            <span className="w-2 h-2 rounded-full" style={{ background: m.user_colour }} />
            {m.user_name}
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                if (!confirm(`Remove ${m.user_name} from ${club.name}?`)) return
                void act(async () => { await api.removeBookClubMember(club.id, m.id); await onChanged() })
              }}
              className="grid min-h-10 min-w-10 place-items-center text-lg text-muted hover:text-danger disabled:opacity-40"
              aria-label={`Remove ${m.user_name} from ${club.name}`}
            >
              ×
            </button>
          </span>
        ))}
        {availableUsers.length > 0 && (
          <>
            <select aria-label="Person to add" className="min-h-11 rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink" value={memberId} onChange={e => setMemberId(Number(e.target.value))}>
              <option value="">Add member</option>
              {availableUsers.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
            </select>
            <Button type="button" size="sm" variant="secondary" loading={busy} disabled={!memberId} onClick={() => act(async () => {
              await api.addBookClubMember(club.id, Number(memberId))
              setMemberId('')
              await onChanged()
            })}>
              Add
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

export function BooksPage() {
  const [surface, setSurface] = useState<Surface>('personal')
  const [activeShelf, setActiveShelf] = useState<BookShelfStatus>('backlog')
  const [showAdd, setShowAdd] = useState(false)
  useUrlAction('book', () => setShowAdd(true))
  const [showClubItems, setShowClubItems] = useState(true)
  const [query, setQuery] = useUrlQueryState()
  const [personal, setPersonal] = useState<PersonalBookEntry[]>([])
  const [clubShelf, setClubShelf] = useState<ClubBookEntry[]>([])
  const [clubs, setClubs] = useState<BookClub[]>([])
  const [users, setUsers] = useState<BooksUser[]>([])
  const [selectedClubId, setSelectedClubId] = useState<number | null>(null)
  const [clubBooks, setClubBooks] = useState<ClubBookEntry[]>([])
  const [queue, setQueue] = useState<ClubQueueItem[]>([])
  const [newClubName, setNewClubName] = useState('')
  const [sortHistoryByRating, setSortHistoryByRating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const selectedClub = useMemo(
    () => clubs.find(c => c.id === selectedClubId) || clubs[0] || null,
    [clubs, selectedClubId],
  )

  const loadCore = async () => {
    setError(null)
    try {
      const [shelves, clubList, userList] = await Promise.all([
        api.getPersonalBooks(showClubItems),
        api.getBookClubs(),
        api.getBooksUsers(),
      ])
      setPersonal(shelves.personal)
      setClubShelf(shelves.club)
      setClubs(clubList)
      setUsers(userList)
      if (!selectedClubId && clubList[0]) setSelectedClubId(clubList[0].id)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }

  const loadClub = async (clubId = selectedClub?.id) => {
    if (!clubId) {
      setClubBooks([])
      setQueue([])
      return
    }
    try {
      const [books, q] = await Promise.all([api.getClubBooks(clubId), api.getClubQueue(clubId)])
      setClubBooks(books)
      setQueue(q)
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const reloadAll = async () => {
    await loadCore()
    await loadClub()
  }

  const act = async (work: () => Promise<void>) => {
    setError(null)
    try {
      await work()
    } catch (e) {
      setError(errMsg(e))
    }
  }

  useEffect(() => { loadCore() }, [showClubItems])
  useEffect(() => { loadClub(selectedClub?.id) }, [selectedClub?.id])

  const matchesQuery = (book: Book) => {
    const q = query.trim().toLowerCase()
    return !q || `${book.title} ${book.author} ${book.genre}`.toLowerCase().includes(q)
  }
  const personalItems = sorted(personal.filter(i => i.status === activeShelf && matchesQuery(i.book)))
  const clubShelfItems = sorted(clubShelf.filter(i => i.status === activeShelf && matchesQuery(i.book)))
  const visibleClubBooks = useMemo(() => {
    const q = query.trim().toLowerCase()
    const items = sorted(clubBooks.filter(i =>
      i.status === activeShelf
      && (!q || `${i.book.title} ${i.book.author} ${i.book.genre}`.toLowerCase().includes(q)),
    ))
    if (activeShelf === 'history' && sortHistoryByRating) {
      return [...items].sort((a, b) => (b.average_rating ?? -1) - (a.average_rating ?? -1))
    }
    return items
  }, [clubBooks, activeShelf, sortHistoryByRating, query])
  const personalCounts = statuses.map(s => ({
    status: s,
    count: personal.filter(i => i.status === s).length,
  }))
  const clubCounts = statuses.map(s => ({
    status: s,
    count: clubBooks.filter(i => i.status === s).length,
  }))

  return (
    <div className="space-y-5">
      <PageHeader
        title="Books"
        icon="📚"
        subtitle="Personal shelves and shared book clubs."
        mobile="show"
        actions={<Button type="button" onClick={() => setShowAdd(v => !v)}>{showAdd ? 'Close' : '+ Add book'}</Button>}
      />

      <SearchField value={query} onChange={event => setQuery(event.target.value)} onClear={() => setQuery('')} placeholder="Search your books and clubs…" />

      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}

      <Tabs
        tabs={[
          { key: 'personal', label: 'My books' },
          { key: 'club', label: 'Book clubs', badge: clubs.length || undefined },
        ]}
        active={surface}
        onChange={setSurface}
        mobileSelectLabel="Books section"
      />

      {showAdd && (
        <AddBookPanel
          mode={surface}
          clubs={clubs}
          selectedClub={selectedClub}
          defaultStatus={activeShelf}
          onClose={() => setShowAdd(false)}
          onAdded={reloadAll}
        />
      )}

      {surface === 'club' && (
        <div className="space-y-3">
          <div className="flex flex-col md:flex-row gap-2 md:items-center">
            <div className="flex flex-wrap gap-2 flex-1">
              {clubs.map(c => (
                <TabButton key={c.id} active={selectedClub?.id === c.id} onClick={() => setSelectedClubId(c.id)} colour={c.colour}>
                  {c.name}
                </TabButton>
              ))}
            </div>
            <input className={`${inputCls} md:max-w-xs`} value={newClubName} onChange={e => setNewClubName(e.target.value)} placeholder="New club name" />
            <Button
              type="button"
              disabled={!newClubName.trim()}
              onClick={() => act(async () => {
                const club = await api.createBookClub({ name: newClubName.trim(), colour: '#8B5CF6' })
                setNewClubName('')
                setSelectedClubId(club.id)
                await reloadAll()
              })}
            >
              Create club
            </Button>
          </div>
          {selectedClub && <ClubSettings club={selectedClub} users={users} onChanged={reloadAll} />}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <Tabs
          tabs={statuses.map(status => ({
            key: status,
            label: shelfLabels[status],
            badge: surface === 'club'
              ? clubCounts.find(row => row.status === status)?.count || undefined
              : personalCounts.find(row => row.status === status)?.count || undefined,
          }))}
          active={activeShelf}
          onChange={setActiveShelf}
          mobileSelectLabel="Book shelf"
        />
        {surface === 'personal' && (
          <label className="inline-flex items-center gap-2 text-sm text-muted-strong">
            <input type="checkbox" checked={showClubItems} onChange={e => setShowClubItems(e.target.checked)} />
            Show book club items
          </label>
        )}
        {surface === 'club' && activeShelf === 'history' && (
          <label className="inline-flex items-center gap-2 text-sm text-muted-strong">
            <input type="checkbox" checked={sortHistoryByRating} onChange={e => setSortHistoryByRating(e.target.checked)} />
            Sort by rating
          </label>
        )}
      </div>

      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : surface === 'personal' ? (
        <div className="grid xl:grid-cols-[minmax(0,1fr)_22rem] gap-5 items-start">
          <div className="space-y-3">
            {personalItems.length > 0 ? (
              <div className="grid lg:grid-cols-2 2xl:grid-cols-3 gap-3">
                {personalItems.map(entry => (
                  <PersonalBookCard
                    key={entry.id}
                    entry={entry}
                    clubs={clubs}
                    onRefresh={reloadAll}
                    onMove={status => act(async () => { await api.updatePersonalBook(entry.id, { status }); await reloadAll() })}
                    onDelete={() => {
                      if (!confirm(`Remove "${entry.book.title}" from your books?`)) return Promise.resolve()
                      return act(async () => { await api.deletePersonalBook(entry.id); await reloadAll() })
                    }}
                    onAddToClub={clubId => act(async () => { await api.createClubBook(clubId, { book_id: entry.book_id, status: 'backlog', position: 0 }); await reloadAll() })}
                  />
                ))}
              </div>
            ) : (
              <Card><p className="text-muted">Nothing in {shelfLabels[activeShelf].toLowerCase()} yet.</p></Card>
            )}
          </div>

          <aside className="space-y-3 xl:sticky xl:top-20">
            <Card title="My shelves">
              <div className="grid grid-cols-3 xl:grid-cols-1 gap-2">
                {personalCounts.map(row => (
                  <button
                    key={row.status}
                    type="button"
                    onClick={() => setActiveShelf(row.status)}
                    className={`rounded-xl px-3 py-2 text-left ${activeShelf === row.status ? 'bg-primary-soft text-primary' : 'bg-sunken text-muted-strong'}`}
                  >
                    <span className="block text-xs font-semibold uppercase tracking-wide">{shelfLabels[row.status]}</span>
                    <span className="text-lg font-bold">{row.count}</span>
                  </button>
                ))}
              </div>
            </Card>
            {showClubItems && (
              <Card title="From book clubs">
                {clubShelfItems.length === 0 ? (
                  <p className="text-sm text-muted">No club books in this shelf.</p>
                ) : (
                  <div className="space-y-2">
                    {clubShelfItems.map(entry => {
                      const club = clubs.find(c => c.id === entry.club_id)
                      return (
                        <div key={`club-${entry.id}`} className="rounded-xl border border-line bg-surface p-3" style={{ borderLeftColor: club?.colour || '#888', borderLeftWidth: 4 }}>
                          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">{club?.name || 'Book club'}</div>
                          <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
                        </div>
                      )
                    })}
                  </div>
                )}
              </Card>
            )}
          </aside>
        </div>
      ) : selectedClub ? (
        <div className="grid xl:grid-cols-[minmax(0,1fr)_24rem] gap-5 items-start">
          <div className="space-y-3">
            {visibleClubBooks.length > 0 ? (
              <div className="grid lg:grid-cols-2 2xl:grid-cols-3 gap-3">
                {visibleClubBooks.map(entry => (
                  <ClubBookCard
                    key={entry.id}
                    entry={entry}
                    club={selectedClub}
                    onRefresh={reloadAll}
                    onMove={status => act(async () => { await api.updateClubBook(selectedClub.id, entry.id, { status }); await reloadAll() })}
                    onDelete={() => {
                      if (!confirm(`Remove "${entry.book.title}" from ${selectedClub.name}?`)) return Promise.resolve()
                      return act(async () => { await api.deleteClubBook(selectedClub.id, entry.id); await reloadAll() })
                    }}
                    onQueue={() => act(async () => { await api.addClubQueueItem(selectedClub.id, entry.id, queue.length + 1); await loadClub() })}
                  />
                ))}
              </div>
            ) : (
              <Card><p className="text-muted">Nothing in {shelfLabels[activeShelf].toLowerCase()} yet.</p></Card>
            )}
          </div>

          <aside className="space-y-3 xl:sticky xl:top-20">
            <Card title="Club shelves">
              <div className="grid grid-cols-3 xl:grid-cols-1 gap-2">
                {clubCounts.map(row => (
                  <button
                    key={row.status}
                    type="button"
                    onClick={() => setActiveShelf(row.status)}
                    className="rounded-xl px-3 py-2 text-left text-muted-strong"
                    style={activeShelf === row.status ? { background: `${selectedClub.colour}22`, color: selectedClub.colour } : undefined}
                  >
                    <span className="block text-xs font-semibold uppercase tracking-wide">{shelfLabels[row.status]}</span>
                    <span className="text-lg font-bold">{row.count}</span>
                  </button>
                ))}
              </div>
            </Card>
            <Card title="Up next">
              {queue.length === 0 ? (
                <p className="text-sm text-muted">No upcoming order yet.</p>
              ) : (
                <div className="space-y-2">
                  {queue.map((item, idx) => (
                    <div key={item.id} className="flex items-center gap-2 rounded-xl bg-sunken p-2">
                      <span className="text-xs font-bold text-muted w-5">{idx + 1}</span>
                      <BookLine title={item.club_book.book.title} author={item.club_book.book.author} />
                      <button
                        type="button"
                        aria-label={`Move ${item.club_book.book.title} up`}
                        disabled={idx === 0}
                        onClick={() => act(async () => { await api.updateClubQueueItem(selectedClub.id, item.id, Math.max(0, item.position - 2)); await loadClub() })}
                        className="ml-auto min-h-10 px-2 text-xs font-semibold text-muted hover:text-primary disabled:opacity-30"
                      >
                        Up
                      </button>
                      <button
                        type="button"
                        aria-label={`Move ${item.club_book.book.title} down`}
                        disabled={idx === queue.length - 1}
                        onClick={() => act(async () => { await api.updateClubQueueItem(selectedClub.id, item.id, item.position + 2); await loadClub() })}
                        className="min-h-10 px-2 text-xs font-semibold text-muted hover:text-primary disabled:opacity-30"
                      >
                        Down
                      </button>
                      <button
                        type="button"
                        aria-label={`Remove ${item.club_book.book.title} from up next`}
                        onClick={() => act(async () => { await api.deleteClubQueueItem(selectedClub.id, item.id); await loadClub() })}
                        className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </aside>
        </div>
      ) : (
        <Card><p className="text-muted">Create a book club to share a reading list.</p></Card>
      )}
    </div>
  )
}
