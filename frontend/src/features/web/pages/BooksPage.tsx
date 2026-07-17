import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../../../api/client'
import type {
  BookClub, BookShelfStatus, BooksUser, ClubBookEntry, ClubQueueItem, PersonalBookEntry,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'

type Surface = 'personal' | 'club'

const inputCls = 'w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]'
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

  useEffect(() => setStatus(defaultStatus), [defaultStatus])
  useEffect(() => setClubId(selectedClub?.id || clubs[0]?.id || ''), [selectedClub?.id, clubs.length])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
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
      await onAdded()
      onClose()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid md:grid-cols-[1.3fr_1fr_7rem_1fr] gap-2">
          <input className={inputCls} value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" />
          <input className={inputCls} value={author} onChange={e => setAuthor(e.target.value)} placeholder="Author" />
          <input className={inputCls} type="number" min={1} value={pages} onChange={e => setPages(e.target.value)} placeholder="Pages" />
          <input className={inputCls} value={genre} onChange={e => setGenre(e.target.value)} placeholder="Genre" />
        </div>
        <div className="grid md:grid-cols-[1fr_1fr_auto_auto] gap-2 items-center">
          <select className={inputCls} value={status} onChange={e => setStatus(e.target.value as BookShelfStatus)}>
            {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
          </select>
          {mode === 'club' && (
            <select className={inputCls} value={clubId} onChange={e => setClubId(Number(e.target.value))}>
              {clubs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          )}
          <Button type="submit" loading={busy} disabled={!title.trim() || (mode === 'club' && !clubId)}>Add book</Button>
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
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

  useEffect(() => setClubId(clubs[0]?.id || ''), [clubs.length])

  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-3">
      <div className="flex items-start gap-2">
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <button type="button" onClick={onDelete} className="ml-auto text-muted hover:text-danger text-xl leading-none" title="Remove">×</button>
      </div>
      <div className="grid sm:grid-cols-[1fr_auto] gap-2">
        <select className={inputCls} value={entry.status} onChange={e => onMove(e.target.value as BookShelfStatus)}>
          {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
        </select>
        {entry.status === 'backlog' && clubs.length > 0 && (
          <div className="flex gap-2">
            <select className={`${inputCls} min-w-[9rem]`} value={clubId} onChange={e => setClubId(Number(e.target.value))}>
              {clubs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <Button type="button" size="sm" variant="secondary" disabled={!clubId} onClick={() => onAddToClub(Number(clubId))}>
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
  return (
    <div className="rounded-xl border border-line bg-surface p-3 space-y-3" style={{ borderLeftColor: entry.added_by_colour || club.colour, borderLeftWidth: 4 }}>
      <div className="flex items-start gap-2">
        <BookLine title={entry.book.title} author={entry.book.author} genre={entry.book.genre} pages={entry.book.pages} />
        <button type="button" onClick={onDelete} className="ml-auto text-muted hover:text-danger text-xl leading-none" title="Remove">×</button>
      </div>
      <div className="grid sm:grid-cols-[1fr_auto] gap-2">
        <select className={inputCls} value={entry.status} onChange={e => onMove(e.target.value as BookShelfStatus)}>
          {statuses.map(s => <option key={s} value={s}>{shelfLabels[s]}</option>)}
        </select>
        {entry.status === 'backlog' && (
          <Button type="button" size="sm" variant="secondary" onClick={onQueue}>Add up next</Button>
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

  useEffect(() => {
    setName(club.name)
    setColour(club.colour)
  }, [club.id, club.name, club.colour])

  const memberIds = new Set(club.memberships.map(m => m.user_id))
  const availableUsers = users.filter(u => !memberIds.has(u.id))

  return (
    <div className="space-y-3 rounded-xl bg-sunken p-3">
      <div className="grid md:grid-cols-[1fr_3.5rem_auto] gap-2">
        <input className={inputCls} value={name} onChange={e => setName(e.target.value)} />
        <input type="color" value={colour} onChange={e => setColour(e.target.value)} className="w-full h-11 rounded-xl border border-line p-1 bg-surface" />
        <Button type="button" variant="secondary" onClick={async () => { await api.updateBookClub(club.id, { name, colour }); await onChanged() }}>
          Save club
        </Button>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {club.memberships.map(m => (
          <span key={m.id} className="inline-flex items-center gap-1.5 rounded-full bg-surface px-2.5 py-1 text-xs text-muted-strong">
            <span className="w-2 h-2 rounded-full" style={{ background: m.user_colour }} />
            {m.user_name}
            <button type="button" onClick={async () => { await api.removeBookClubMember(club.id, m.id); await onChanged() }} className="text-muted hover:text-danger">×</button>
          </span>
        ))}
        {availableUsers.length > 0 && (
          <>
            <select className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink" value={memberId} onChange={e => setMemberId(Number(e.target.value))}>
              <option value="">Add member</option>
              {availableUsers.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
            </select>
            <Button type="button" size="sm" variant="secondary" disabled={!memberId} onClick={async () => {
              await api.addBookClubMember(club.id, Number(memberId))
              setMemberId('')
              await onChanged()
            }}>
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
  const [showClubItems, setShowClubItems] = useState(true)
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

  useEffect(() => { loadCore() }, [showClubItems])
  useEffect(() => { loadClub(selectedClub?.id) }, [selectedClub?.id])

  const personalItems = sorted(personal.filter(i => i.status === activeShelf))
  const clubShelfItems = sorted(clubShelf.filter(i => i.status === activeShelf))
  const visibleClubBooks = useMemo(() => {
    const items = sorted(clubBooks.filter(i => i.status === activeShelf))
    if (activeShelf === 'history' && sortHistoryByRating) {
      return [...items].sort((a, b) => (b.average_rating ?? -1) - (a.average_rating ?? -1))
    }
    return items
  }, [clubBooks, activeShelf, sortHistoryByRating])
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
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Books</h1>
          <p className="text-muted mt-1">Personal shelves and shared book clubs.</p>
        </div>
        <Button type="button" onClick={() => setShowAdd(v => !v)}>{showAdd ? 'Close' : '+ Add book'}</Button>
      </div>

      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}

      <div className="flex flex-wrap gap-2">
        <TabButton active={surface === 'personal'} onClick={() => setSurface('personal')}>Individual</TabButton>
        <TabButton active={surface === 'club'} onClick={() => setSurface('club')} colour={selectedClub?.colour}>Book club</TabButton>
      </div>

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
              onClick={async () => {
                const club = await api.createBookClub({ name: newClubName.trim(), colour: '#8B5CF6' })
                setNewClubName('')
                setSelectedClubId(club.id)
                await reloadAll()
              }}
            >
              Create club
            </Button>
          </div>
          {selectedClub && <ClubSettings club={selectedClub} users={users} onChanged={reloadAll} />}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {statuses.map(s => (
            <TabButton key={s} active={activeShelf === s} onClick={() => setActiveShelf(s)} colour={surface === 'club' ? selectedClub?.colour : undefined}>
              {shelfLabels[s]}
            </TabButton>
          ))}
        </div>
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
                    onMove={async status => { await api.updatePersonalBook(entry.id, { status }); await reloadAll() }}
                    onDelete={async () => { await api.deletePersonalBook(entry.id); await reloadAll() }}
                    onAddToClub={async clubId => { await api.createClubBook(clubId, { book_id: entry.book_id, status: 'backlog', position: 0 }); await reloadAll() }}
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
                    onMove={async status => { await api.updateClubBook(selectedClub.id, entry.id, { status }); await reloadAll() }}
                    onDelete={async () => { await api.deleteClubBook(selectedClub.id, entry.id); await reloadAll() }}
                    onQueue={async () => { await api.addClubQueueItem(selectedClub.id, entry.id, queue.length + 1); await loadClub() }}
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
                      <button disabled={idx === 0} onClick={async () => { await api.updateClubQueueItem(selectedClub.id, item.id, Math.max(0, item.position - 2)); await loadClub() }} className="ml-auto text-xs text-muted hover:text-primary disabled:opacity-30">Up</button>
                      <button onClick={async () => { await api.updateClubQueueItem(selectedClub.id, item.id, item.position + 2); await loadClub() }} className="text-xs text-muted hover:text-primary">Down</button>
                      <button onClick={async () => { await api.deleteClubQueueItem(selectedClub.id, item.id); await loadClub() }} className="text-muted hover:text-danger text-xl leading-none">×</button>
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
