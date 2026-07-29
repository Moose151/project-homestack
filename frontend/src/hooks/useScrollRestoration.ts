import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const PREFIX = 'hs-scroll:'

/** Restore the previous vertical position when browser history returns to a route. */
export function useScrollRestoration() {
  const location = useLocation()

  useEffect(() => {
    const key = `${PREFIX}${location.key}`
    const saved = sessionStorage.getItem(key)
    const frame = requestAnimationFrame(() => {
      window.scrollTo({ top: saved ? Number(saved) : 0, behavior: 'auto' })
    })
    return () => {
      cancelAnimationFrame(frame)
      sessionStorage.setItem(key, String(window.scrollY))
    }
  }, [location.key])
}
