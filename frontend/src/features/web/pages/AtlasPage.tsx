import { useEffect, useRef, useState } from 'react'
import { api } from '../../../api/client'
import type { AtlasList, AtlasListItem, AtlasReminder } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'

// ---------------------------------------------------------------------------
// List item row
// ---------------------------------------------------------------------------

function ItemRow({
  item,
  listId,
  onToggle,
  onDelete,
}: {
  item: AtlasListItem
  listId: number
  onToggle: (item: AtlasListItem) => void
  onDelete: (item: AtlasListItem) => void
}) {
  const [busy, setBusy] = useState(false)

  const toggle = async () => {
    setBusy(true)
    try {
      const updated = item.is_complete
        ? await api.uncompleteItem(listId, item.id)
        : await api.completeItem(listId, item.id)
      onToggle(updated)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="flex items-center gap-3 py-2 group">
      <button
        onClick={toggle}
        disabled={busy}
        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${
          item.is_complete
            ? 'bg-green-500 border-green-500 text-white'
            : 'border-gray-300 dark:border-gray-600 hover:border-green-400'
        }`}
        aria-label={item.is_complete ? 'Uncheck' : 'Check'}
      >
        {item.is_complete && <span className="text-xs">✓</span>}
      </button>
      <span className={`flex-1 text-sm ${item.is_complete ? 'line-through text-gray-400' : 'text-gray-800 dark:text-gray-200'}`}>
        {item.title}
      </span>
      <button
        onClick={() => onDelete(item)}
        className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition-all text-lg leading-none"
        aria-label="Delete"
      >
        ×
      </button>
    </li>
  )
}

// ---------------------------------------------------------------------------
// Single list card
// ---------------------------------------------------------------------------

function ListCard({ list, onDeleted }: { list: AtlasList; onDeleted: (id: number) => void }) {
  const [items, setItems] = useState<AtlasListItem[]>(list.items)
  const [newTitle, setNewTitle] = useState('')
  const [adding, setAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      const item = await api.createItem(list.id, { title: newTitle.trim() })
      setItems(prev => [...prev, item])
      setNewTitle('')
      inputRef.current?.focus()
    } finally {
      setAdding(false)
    }
  }

  const handleToggle = (updated: AtlasListItem) => {
    setItems(prev => prev.map(i => i.id === updated.id ? updated : i))
  }

  const handleDelete = async (item: AtlasListItem) => {
    await api.deleteItem(list.id, item.id).catch(() => {})
    setItems(prev => prev.filter(i => i.id !== item.id))
  }

  const deleteList = async () => {
    if (!confirm(`Delete "${list.title}"?`)) return
    await api.deleteList(list.id).catch(() => {})
    onDeleted(list.id)
  }

  const pending = items.filter(i => !i.is_complete)
  const done = items.filter(i => i.is_complete)

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">{list.title}</h3>
          <span className="text-xs text-gray-400 capitalize">{list.list_type}</span>
        </div>
        <button
          onClick={deleteList}
          className="text-gray-300 hover:text-red-400 transition-colors text-xl leading-none"
          aria-label="Delete list"
        >
          ×
        </button>
      </div>

      <ul className="divide-y divide-gray-50 dark:divide-gray-700/50">
        {pending.map(item => (
          <ItemRow key={item.id} item={item} listId={list.id} onToggle={handleToggle} onDelete={handleDelete} />
        ))}
        {done.map(item => (
          <ItemRow key={item.id} item={item} listId={list.id} onToggle={handleToggle} onDelete={handleDelete} />
        ))}
      </ul>

      <form onSubmit={addItem} className="flex gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        <input
          ref={inputRef}
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="Add item…"
          className="flex-1 text-sm bg-transparent text-gray-800 dark:text-gray-200 placeholder-gray-400 outline-none min-h-[36px]"
        />
        <Button type="submit" size="sm" loading={adding} disabled={!newTitle.trim()}>
          Add
        </Button>
      </form>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Reminders tab
// ---------------------------------------------------------------------------

function RemindersTab() {
  const [reminders, setReminders] = useState<AtlasReminder[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getReminders().then(setReminders).finally(() => setLoading(false))
  }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      const r = await api.createReminder({ title: title.trim(), due_at: dueAt || undefined })
      setReminders(prev => [...prev, r])
      setTitle('')
      setDueAt('')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number) => {
    await api.deleteReminder(id).catch(() => {})
    setReminders(prev => prev.filter(r => r.id !== id))
  }

  if (loading) return <div className="h-32 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <Card title="New reminder">
        <form onSubmit={create} className="flex flex-col gap-3">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Reminder title"
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-transparent text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <input
              type="datetime-local"
              value={dueAt}
              onChange={e => setDueAt(e.target.value)}
              className="flex-1 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-600 bg-transparent text-sm text-gray-700 dark:text-gray-300 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Button type="submit" loading={saving} disabled={!title.trim()}>
              Save
            </Button>
          </div>
        </form>
      </Card>

      {reminders.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-6">No reminders yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {reminders.map(r => (
            <Card key={r.id}>
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 dark:text-gray-200">{r.title}</p>
                  {r.body && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{r.body}</p>}
                  {r.due_at && (
                    <p className="text-xs text-blue-500 mt-1">
                      {new Date(r.due_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => remove(r.id)}
                  className="text-gray-300 hover:text-red-400 transition-colors text-xl leading-none flex-shrink-0"
                  aria-label="Delete"
                >
                  ×
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Atlas page
// ---------------------------------------------------------------------------

type Tab = 'lists' | 'reminders'

export function AtlasPage() {
  const [tab, setTab] = useState<Tab>('lists')
  const [lists, setLists] = useState<AtlasList[]>([])
  const [loading, setLoading] = useState(true)
  const [newTitle, setNewTitle] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api.getLists().then(setLists).finally(() => setLoading(false))
  }, [])

  const createList = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setCreating(true)
    try {
      const list = await api.createList({ title: newTitle.trim(), list_type: 'todo' })
      // Fetch the full list (with items array) after creation
      const full = await api.getList(list.id)
      setLists(prev => [full, ...prev])
      setNewTitle('')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Atlas</h1>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
        {(['lists', 'reminders'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              tab === t
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'lists' ? (
        <div className="flex flex-col gap-4">
          <form onSubmit={createList} className="flex gap-2">
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="New list name…"
              className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Button type="submit" loading={creating} disabled={!newTitle.trim()}>
              Create
            </Button>
          </form>

          {loading ? (
            <div className="h-32 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ) : lists.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No lists yet. Create one above.</p>
          ) : (
            lists.map(list => (
              <ListCard
                key={list.id}
                list={list}
                onDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
              />
            ))
          )}
        </div>
      ) : (
        <RemindersTab />
      )}
    </div>
  )
}
