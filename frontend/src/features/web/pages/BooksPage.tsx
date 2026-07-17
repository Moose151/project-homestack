import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api } from '../../../api/client'
import type {
  BookClub, BookShelfStatus, BooksUser, ClubBookEntry, ClubQueueItem, PersonalBookEntry,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'

const inputCls = 'w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]'
const shelfLabels: Record<BookShelfStatus, string> = { backlog: 'Backlog', reading: 'Reading', history: 'History' }
const statuses: BookShelfStatus[] = ['backlog', 'reading', 'history']

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

function byShelf<T extends { status: BookShelfStatus; position: number; created_at: string }>(items: T[], status: BookShelfStatus) {
  return items
    .filter(i => i.status === status)
    .sort((a, b) => a.position - b.position || a.created_at.localeCompare(b.created_at))
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

function RatingEditor({ bookId, rating, notes, onSaved }: {
  bookId: number
  rating: number | null
  notes: string
  onSaved: () => void
}) {
  const [value, setValue] = useState(rating ?? '')
  const [text, setText] = useState(notes || '')
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setValue(rating ?? '')
    setText(notes || '')
  }, [rating, notes])

  const save = async () => {
    setBusy(true)
    try {
      await api.upsertBookRating({
        book_id: bookId,
        rating: value === '' ? null : Number(value),
        notes: text,
      })
      setOpen(false)
      onSaved()
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => setOpen(v => !v)}
        className="text-xs font-semibold text-primary hover:underline"
      >
        {rating == null ? 'Rate / notes' : `${rating}/10 · notes`}
      </button>
      {open && (
        <div className="grid gap-2 bg-sunken rounded-xl p-2">
          <div className="flex gap-2">
            <input
              type="number"
              min={0}
              max={10}
              className={`${inputCls} max-w-[6rem]`}
              value={value}
              onChange={e => setValue(e.target.value === '' ? '' : Number(e.target.value))}
            />
            <Button type="button" size="sm" loading={busy} onClick={save}>Save</Button>
          </div>
          <textarea
            className={`${inputCls} min-h-[72px] resize-none`}
            placeholder="Notes"
            value={text}
            onChange={e => setText(e.target.value)}
          />
        </div>
      )}
    </div>
  )
}

function AddBookForm({ onAdd, label = 'Add book' }: {
  label?: string
  onAdd: (data: { title: string; author: string; pages: number | null; genre: string }) => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [pages, setPages] = useState('')
  const [genre, setGenre] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      await onAdd({
        title: title.trim(),
        author: author.trim(),
        pages: pages ? Number(pages) : null,
        genre: genre.trim(),
      })
      setTitle('')
      setAuthor('')
      setPages('')
      setGenre('')
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="grid md:grid-cols-[1.4fr_1fr_7rem_1fr_auto] gap-2">
      <input className={inputCls} value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" />
      <input className={inputCls} value={author} onChange={e => setAuthor(e.target.value)} placeholder="Author" />
      <input className={inputCls} type="number" min={1} value={pages} onChange={e => setPages(e.target.value)} placeholder="Pages" />
      <input className={inputCls} value={genre} onChange={e => setGenre(e.target.value)} placeholder="Genre" />
      <Button type="submit" loading={busy}>{label}</Button>
    </form>
  )
}

function PersonalCard({ entry, onRefresh, onMove, onDelete }: {
  entry: PersonalBookEntry
  onRefresh: () => void
  onMove: (status: BookShelfStatus) => void
  onDelete: () => void
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-2">
      <div className="flex items-start gap-2">
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <button onClick={onDelete} className="ml-auto text-muted hover:text-danger text-xl leading-none" title="Remove">×</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {statuses.map(s => (
          <button
            key={s}
            onClick={() => onMove(s)}
            className={`px-2 py-1 rounded-lg text-xs font-semibold ${entry.status === s ? 'bg-primary text-white' : 'bg-sunken text-muted-strong'}`}
          >
            {shelfLabels[s]}
          </button>
        ))}
      </div>
      <RatingEditor bookId={entry.book_id} rating={entry.rating} notes={entry.notes} onSaved={onRefresh} />
    </div>
  )
}

function ClubBookCard({ entry, club, onRefresh, onMove, onDelete, onQueue }: {
  entry: ClubBookEntry
  club: BookClub
  onRefresh: () => void
  onMove: (status: BookShelfStatus) => void
  onDelete: () => void
  onQueue?: () => void
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-2">
      <div className="flex items-start gap-2">
        <span
          className="mt-1 w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ background: entry.added_by_colour || club.colour }}
          title={entry.added_by_name ? `Added by ${entry.added_by_name}` : club.name}
        />
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <button onClick={onDelete} className="ml-auto text-muted hover:text-danger text-xl leading-none" title="Remove">×</button>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {statuses.map(s => (
          <button
            key={s}
            onClick={() => onMove(s)}
            className={`px-2 py-1 rounded-lg text-xs font-semibold ${entry.status === s ? 'text-white' : 'bg-sunken text-muted-strong'}`}
            style={entry.status === s ? { background: club.colour } : undefined}
          >
            {shelfLabels[s]}
          </button>
        ))}
        {entry.status === 'backlog' && onQueue && (
          <button onClick={onQueue} className="px-2 py-1 rounded-lg text-xs font-semibold bg-sunken text-muted-strong">Up next</button>
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
      <RatingEditor bookId={entry.book_id} rating={entry.my_rating} notes={entry.ratings.find(r => r.book_id === entry.book_id)?.notes || ''} onSaved={onRefresh} />
    </div>
  )
}

function ShelfColumn({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {children}
    </div>
  )
}

function ClubPanel({ club, users, onClubChanged, onError }: {
  club: BookClub
  users: BooksUser[]
  onClubChanged: () => void
  onError: (m: string) => void
}) {
  const [books, setBooks] = useState<ClubBookEntry[]>([])
  const [queue, setQueue] = useState<ClubQueueItem[]>([])
  const [name, setName] = useState(club.name)
  const [colour, setColour] = useState(club.colour)
  const [memberId, setMemberId] = useState('')
  const [sortHistoryByRating, setSortHistoryByRating] = useState(false)

  const load = async () => {
    try {
      const [b, q] = await Promise.all([api.getClubBooks(club.id), api.getClubQueue(club.id)])
      setBooks(b)
      setQueue(q)
    } catch (e) { onError(errMsg(e)) }
  }

  useEffect(() => {
    setName(club.name)
    setColour(club.colour)
    load()
  }, [club.id])

  const refreshAll = async () => {
    await load()
    onClubChanged()
  }

  const memberIds = new Set(club.memberships.map(m => m.user_id))
  const availableUsers = users.filter(u => !memberIds.has(u.id))

  return (
    <Card>
      <div className="space-y-5">
        <div className="flex flex-col md:flex-row gap-2 md:items-center">
          <input className={inputCls} value={name} onChange={e => setName(e.target.value)} />
          <input type="color" value={colour} onChange={e => setColour(e.target.value)} className="w-12 h-11 rounded-xl border border-line p-1 bg-surface" />
          <Button
            type="button"
            variant="secondary"
            onClick={async () => { await api.updateBookClub(club.id, { name, colour }); onClubChanged() }}
          >
            Save club
          </Button>
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          {club.memberships.map(m => (
            <span key={m.id} className="inline-flex items-center gap-1.5 rounded-full bg-sunken px-2.5 py-1 text-xs text-muted-strong">
              <span className="w-2 h-2 rounded-full" style={{ background: m.user_colour }} />
              {m.user_name}
              <button onClick={async () => { await api.removeBookClubMember(club.id, m.id); onClubChanged() }} className="text-muted hover:text-danger">×</button>
            </span>
          ))}
          {availableUsers.length > 0 && (
            <>
              <select className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink" value={memberId} onChange={e => setMemberId(e.target.value)}>
                <option value="">Add member</option>
                {availableUsers.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
              </select>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!memberId}
                onClick={async () => { await api.addBookClubMember(club.id, Number(memberId)); setMemberId(''); onClubChanged() }}
              >
                Add
              </Button>
            </>
          )}
        </div>

        <AddBookForm
          label="Add to club"
          onAdd={async book => {
            await api.createClubBook(club.id, { book, status: 'backlog', position: books.length + 1 })
            await load()
          }}
        />

        <div className="grid md:grid-cols-2 gap-4">
          <ShelfColumn title="Up next">
            {queue.length === 0 && <p className="text-sm text-muted">No upcoming order yet.</p>}
            {queue.map((item, idx) => (
              <div key={item.id} className="rounded-xl border border-line bg-surface p-3">
                <div className="flex gap-2 items-start">
                  <span className="text-xs font-bold text-muted w-5">{idx + 1}</span>
                  <BookLine title={item.club_book.book.title} author={item.club_book.book.author} />
                  <button onClick={async () => { await api.deleteClubQueueItem(club.id, item.id); await load() }} className="ml-auto text-muted hover:text-danger text-xl leading-none">×</button>
                </div>
                <div className="flex gap-1 mt-2">
                  <button disabled={idx === 0} onClick={async () => { await api.updateClubQueueItem(club.id, item.id, Math.max(0, item.position - 2)); await load() }} className="text-xs text-muted hover:text-primary disabled:opacity-30">↑</button>
                  <button onClick={async () => { await api.updateClubQueueItem(club.id, item.id, item.position + 2); await load() }} className="text-xs text-muted hover:text-primary">↓</button>
                </div>
              </div>
            ))}
          </ShelfColumn>
          {statuses.map(status => {
            const shelfItems = byShelf(books, status)
            const visibleItems = status === 'history' && sortHistoryByRating
              ? [...shelfItems].sort((a, b) => (b.average_rating ?? -1) - (a.average_rating ?? -1))
              : shelfItems
            return (
            <ShelfColumn key={status} title={shelfLabels[status]}>
              {status === 'history' && (
                <label className="inline-flex items-center gap-2 text-xs text-muted-strong mb-1">
                  <input type="checkbox" checked={sortHistoryByRating} onChange={e => setSortHistoryByRating(e.target.checked)} />
                  Sort by rating
                </label>
              )}
              {visibleItems.length === 0 && <p className="text-sm text-muted">Nothing here.</p>}
              {visibleItems.map(entry => (
                <ClubBookCard
                  key={entry.id}
                  entry={entry}
                  club={club}
                  onRefresh={refreshAll}
                  onMove={async s => { await api.updateClubBook(club.id, entry.id, { status: s }); await load() }}
                  onDelete={async () => { await api.deleteClubBook(club.id, entry.id); await load() }}
                  onQueue={async () => { await api.addClubQueueItem(club.id, entry.id, queue.length + 1); await load() }}
                />
              ))}
            </ShelfColumn>
          )})}
        </div>
      </div>
    </Card>
  )
}

export function BooksPage() {
  const [personal, setPersonal] = useState<PersonalBookEntry[]>([])
  const [clubShelf, setClubShelf] = useState<ClubBookEntry[]>([])
  const [clubs, setClubs] = useState<BookClub[]>([])
  const [users, setUsers] = useState<BooksUser[]>([])
  const [selectedClubId, setSelectedClubId] = useState<number | null>(null)
  const [showClubItems, setShowClubItems] = useState(true)
  const [newClubName, setNewClubName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const selectedClub = useMemo(
    () => clubs.find(c => c.id === selectedClubId) || clubs[0] || null,
    [clubs, selectedClubId],
  )

  const load = async () => {
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
    } catch (e) { setError(errMsg(e)) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [showClubItems])

  const refreshShelves = async () => {
    const shelves = await api.getPersonalBooks(showClubItems)
    setPersonal(shelves.personal)
    setClubShelf(shelves.club)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Books</h1>
          <p className="text-muted mt-1">Personal shelves and shared book clubs.</p>
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-muted-strong">
          <input type="checkbox" checked={showClubItems} onChange={e => setShowClubItems(e.target.checked)} />
          Show book club items on my shelves
        </label>
      </div>

      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}

      <Card title="Add to my books">
        <AddBookForm
          onAdd={async book => {
            await api.createPersonalBook({ book, status: 'backlog', position: personal.length + 1 })
            await refreshShelves()
          }}
        />
      </Card>

      {loading ? (
        <p className="text-muted">Loading…</p>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {statuses.map(status => (
            <ShelfColumn key={status} title={`My ${shelfLabels[status]}`}>
              {byShelf(personal, status).map(entry => (
                <PersonalCard
                  key={entry.id}
                  entry={entry}
                  onRefresh={refreshShelves}
                  onMove={async s => { await api.updatePersonalBook(entry.id, { status: s }); await refreshShelves() }}
                  onDelete={async () => { await api.deletePersonalBook(entry.id); await refreshShelves() }}
                />
              ))}
              {showClubItems && byShelf(clubShelf, status).map(entry => (
                <div key={`club-${entry.id}`} className="rounded-xl border border-line bg-surface p-3" style={{ borderLeftColor: clubs.find(c => c.id === entry.club_id)?.colour || '#888', borderLeftWidth: 4 }}>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    {clubs.find(c => c.id === entry.club_id)?.name || 'Book club'}
                  </div>
                  <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
                </div>
              ))}
              {byShelf(personal, status).length === 0 && (!showClubItems || byShelf(clubShelf, status).length === 0) && (
                <p className="text-sm text-muted">Nothing here.</p>
              )}
            </ShelfColumn>
          ))}
        </div>
      )}

      <div className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-center gap-2">
          <h2 className="text-xl font-bold text-ink flex-1">Book clubs</h2>
          <input className={`${inputCls} md:max-w-xs`} value={newClubName} onChange={e => setNewClubName(e.target.value)} placeholder="New club name" />
          <Button
            type="button"
            disabled={!newClubName.trim()}
            onClick={async () => {
              const club = await api.createBookClub({ name: newClubName.trim(), colour: '#8B5CF6' })
              setNewClubName('')
              setSelectedClubId(club.id)
              await load()
            }}
          >
            Create club
          </Button>
        </div>
        {clubs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {clubs.map(c => (
              <button
                key={c.id}
                onClick={() => setSelectedClubId(c.id)}
                className={`px-3 py-2 rounded-xl text-sm font-semibold ${selectedClub?.id === c.id ? 'text-white' : 'bg-sunken text-muted-strong'}`}
                style={selectedClub?.id === c.id ? { background: c.colour } : undefined}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
        {selectedClub ? (
          <ClubPanel
            club={selectedClub}
            users={users}
            onClubChanged={load}
            onError={setError}
          />
        ) : (
          <Card><p className="text-muted">Create a book club to share a reading list.</p></Card>
        )}
      </div>
    </div>
  )
}
