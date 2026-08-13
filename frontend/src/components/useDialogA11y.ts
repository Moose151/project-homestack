import { useEffect, useRef } from 'react'

const dialogStack: symbol[] = []
let bodyOverflowBeforeDialogs: string | null = null

function registerDialog(id: symbol) {
  if (dialogStack.length === 0) {
    bodyOverflowBeforeDialogs = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  dialogStack.push(id)
}

function unregisterDialog(id: symbol) {
  const index = dialogStack.lastIndexOf(id)
  if (index !== -1) dialogStack.splice(index, 1)
  if (dialogStack.length === 0 && bodyOverflowBeforeDialogs !== null) {
    document.body.style.overflow = bodyOverflowBeforeDialogs
    bodyOverflowBeforeDialogs = null
  }
}

const isTopDialog = (id: symbol) => dialogStack[dialogStack.length - 1] === id

/**
 * Shared sheet/dialog accessibility behaviour: Escape-to-close, a Tab focus trap confined to
 * the dialog, autofocus on open (a `[data-autofocus]` element if one exists, else the first
 * focusable control), scroll lock, and restoring focus to whatever triggered the dialog once it
 * closes. Originally lived only in `Modal`; extracted so any other sheet-style surface (the app
 * shell's More sheet, in particular) gets identical behaviour instead of a second hand-rolled
 * implementation that could quietly drift from it.
 */
export function useDialogA11y(onClose: () => void) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const dialogId = useRef(Symbol('dialog')).current
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    registerDialog(dialogId)
    const onKey = (e: KeyboardEvent) => {
      // A confirmation/prompt can be mounted above a full-screen sheet. Only the topmost
      // dialog owns Escape and the focus trap; otherwise one keypress closes every layer.
      if (!isTopDialog(dialogId)) return
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        closeRef.current()
      }
      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        )]
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    const frame = requestAnimationFrame(() => {
      if (!isTopDialog(dialogId)) return
      // React never renders an `autofocus` attribute, so a dialog that wants a specific control
      // focused marks it `data-autofocus`; otherwise focus falls to the first control, which in
      // document order is usually the header's close button.
      const dialog = dialogRef.current
      const preferred = dialog?.querySelector<HTMLElement>('[data-autofocus]')
      ;(preferred ?? dialog?.querySelector<HTMLElement>('input, select, textarea, button'))?.focus()
    })
    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('keydown', onKey)
      unregisterDialog(dialogId)
      if (previouslyFocused?.isConnected) previouslyFocused.focus()
    }
  }, [dialogId])

  return dialogRef
}
