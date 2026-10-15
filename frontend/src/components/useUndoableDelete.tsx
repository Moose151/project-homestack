import { useCallback, useState } from 'react'
import { api } from '../api/client'
import { UndoToast } from './UndoToast'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

export type UndoableDeleteOptions = {
  recordType: string
  id: number
  label: string
  onRestored: () => void | Promise<void>
}

/**
 * Delete now, offer it back — the pattern that replaced "Are you sure?" for routine,
 * single-record deletes (v0.40.10, `backend/apps/core/undo.py` has the rule for which
 * deletes qualify and which keep their confirmation).
 *
 * Shared rather than written out per page, because five nodes were about to grow five
 * slightly different versions of the same three pieces of state — and a delete that reports
 * failure in four of them and swallows it in the fifth is exactly the inconsistency this
 * whole workstream exists to remove.
 *
 * `recordType` must be a key of the backend's restore registry; an unregistered one comes back
 * as a 404 the reader would see only after tapping Undo, which is the wrong time to find out.
 */
export function useUndoableDelete(onError: (message: string) => void) {
  const [pending, setPending] = useState<UndoableDeleteOptions | null>(null)

  const remove = useCallback(async (
    options: UndoableDeleteOptions & { run: () => Promise<unknown> },
  ) => {
    const { run, ...rest } = options
    try {
      await run()
      setPending(rest)
    } catch (e) {
      // A failed delete must say so: without this the row would stay put with no explanation,
      // which reads as the click not having registered.
      onError(errMsg(e))
    }
  }, [onError])

  const undo = useCallback(async () => {
    if (!pending) return
    const target = pending
    setPending(null)
    try {
      await api.restoreRecord(target.recordType, target.id)
      await target.onRestored()
    } catch (e) {
      onError(errMsg(e))
    }
  }, [pending, onError])

  const toast = pending
    ? (
      <UndoToast
        message={`Deleted ${pending.label}`}
        onUndo={undo}
        onDismiss={() => setPending(null)}
      />
    )
    : null

  return { remove, toast }
}

/** The `remove` a page hands to a child that deletes but does not survive the deletion. */
export type UndoableDelete = ReturnType<typeof useUndoableDelete>['remove']
