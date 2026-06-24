import { useCallback, useEffect, useRef } from 'react'

/**
 * Reset the inactivity timeout on every user interaction.
 * Calls onTimeout after `delayMs` of inactivity.
 * Returns a manual reset function for programmatic resets (e.g. after PIN entry).
 */
export function useInactivityTimeout(onTimeout: () => void, delayMs: number = 5 * 60 * 1000) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const reset = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(onTimeout, delayMs)
  }, [onTimeout, delayMs])

  useEffect(() => {
    const events: (keyof DocumentEventMap)[] = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
    const handle = () => reset()

    events.forEach((e) => document.addEventListener(e, handle, { passive: true }))
    reset()

    return () => {
      events.forEach((e) => document.removeEventListener(e, handle))
      if (timer.current) clearTimeout(timer.current)
    }
  }, [reset])

  return reset
}
