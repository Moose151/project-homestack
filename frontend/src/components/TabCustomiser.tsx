import { useEffect, useState } from 'react'
import { Button } from './Button'
import { Modal } from './Modal'
import type { TabDef } from './Tabs'

/**
 * Reorder a page's tabs.
 *
 * Drag-and-drop is offered on pointer devices, but it is never the only way: HTML5 drag events
 * are unreliable under touch, and a drag target is not keyboard-operable. Move up / Move down
 * buttons are the primary mechanism — they work identically with a finger, a mouse and a
 * keyboard — with dragging layered on top for people who reach for it.
 *
 * The first tab in the list becomes the page's landing tab, which the panel states plainly
 * rather than leaving to be discovered.
 */
export function TabCustomiser<T extends string>({
  title,
  tabs,
  isCustomised,
  onSave,
  onReset,
  onClose,
}: {
  title: string
  tabs: TabDef<T>[]
  isCustomised: boolean
  onSave: (order: string[]) => void | Promise<void>
  onReset: () => void | Promise<void>
  onClose: () => void
}) {
  const [order, setOrder] = useState<TabDef<T>[]>(tabs)
  const [dragging, setDragging] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  // Keep in step if the page's tab set changes underneath the open panel (a badge updating, a
  // permission-hidden tab disappearing) without discarding an in-progress reorder.
  //
  // Keyed on the tab identities rather than the array itself: pages that build their tab list
  // inline (Tasks derives it from `canManage`) hand us a fresh array every render, and depending
  // on that identity would re-run this effect forever.
  const identity = tabs.map(tab => tab.key).join('|')
  useEffect(() => {
    setOrder(current => {
      const available = new Map(tabs.map(tab => [tab.key, tab]))
      const kept = current.filter(tab => available.has(tab.key)).map(tab => available.get(tab.key)!)
      const keptKeys = new Set(kept.map(tab => tab.key))
      return [...kept, ...tabs.filter(tab => !keptKeys.has(tab.key))]
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identity])

  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length || from === to) return
    setOrder(current => {
      const next = [...current]
      const [moved] = next.splice(from, 1)
      next.splice(to, 0, moved)
      return next
    })
  }

  const save = async () => {
    setSaving(true)
    try {
      await onSave(order.map(tab => tab.key as string))
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const reset = async () => {
    setSaving(true)
    try {
      await onReset()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={title}
      onClose={onClose}
      size="sm"
      footer={(
        <>
          {isCustomised && (
            <button onClick={reset} className="mr-auto text-sm font-semibold text-muted-strong hover:text-primary hover:underline">
              Reset to default
            </button>
          )}
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={save} loading={saving}>Save order</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted">
          Drag a tab, or use the arrows. The tab at the top becomes the one this page opens on.
        </p>
        <ul className="flex flex-col gap-2" aria-label="Tab order">
          {order.map((tab, index) => (
            <li
              key={tab.key}
              draggable
              onDragStart={() => setDragging(index)}
              onDragOver={event => {
                event.preventDefault()
                if (dragging !== null && dragging !== index) { move(dragging, index); setDragging(index) }
              }}
              onDragEnd={() => setDragging(null)}
              className={`flex items-center gap-2 rounded-xl border bg-surface px-3 py-2 ${
                dragging === index ? 'border-primary shadow-sm' : 'border-line'
              }`}
            >
              <span className="cursor-grab text-muted" aria-hidden>⠿</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold capitalize text-ink">{tab.label}</span>
                {index === 0 && <span className="text-[11px] font-bold text-primary">Opens by default</span>}
              </span>
              <span className="flex flex-shrink-0 items-center gap-1">
                <button
                  type="button"
                  onClick={() => move(index, index - 1)}
                  disabled={index === 0}
                  aria-label={`Move ${tab.label} up`}
                  className="grid h-11 w-11 place-items-center rounded-lg text-muted-strong hover:bg-sunken disabled:opacity-30"
                >↑</button>
                <button
                  type="button"
                  onClick={() => move(index, index + 1)}
                  disabled={index === order.length - 1}
                  aria-label={`Move ${tab.label} down`}
                  className="grid h-11 w-11 place-items-center rounded-lg text-muted-strong hover:bg-sunken disabled:opacity-30"
                >↓</button>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  )
}
