import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/**
 * Keep a page's active tab in the URL so links, refresh and browser history retain context.
 *
 * `param` lets a page keep a second level too — a destination grouped into sections passes
 * "section" for the inner one, so both levels survive a refresh or a shared link.
 */
export function useUrlTab<T extends string>(defaultTab: T, validTabs: readonly T[], param = 'tab') {
  const location = useLocation()
  const navigate = useNavigate()
  const requested = new URLSearchParams(location.search).get(param) as T | null
  const tab = requested && validTabs.includes(requested) ? requested : defaultTab

  const setTab = useCallback((next: T) => {
    const params = new URLSearchParams(location.search)
    if (next === defaultTab) params.delete(param)
    else params.set(param, next)
    const search = params.toString()
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' })
  }, [defaultTab, location.pathname, location.search, navigate, param])

  return [tab, setTab] as const
}

/** Local search input that also reacts when a global-search link targets the current route. */
export function useUrlQueryState(key = 'q') {
  const location = useLocation()
  const urlValue = new URLSearchParams(location.search).get(key)
  const lastUrlValue = useRef<string | null>(urlValue)
  const [value, setValue] = useState(() => urlValue ?? '')

  useEffect(() => {
    if (urlValue === lastUrlValue.current) return
    lastUrlValue.current = urlValue
    setValue(urlValue ?? '')
  }, [urlValue])

  return [value, setValue] as const
}

/** Consume a one-shot `?new=...` action, including when targeting the route already open. */
export function useUrlAction(action: string, onTrigger: () => void) {
  const location = useLocation()
  const navigate = useNavigate()
  const handled = useRef('')

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (params.get('new') !== action) {
      handled.current = ''
      return
    }
    const requestKey = `${location.pathname}${location.search}`
    if (handled.current === requestKey) return
    handled.current = requestKey
    params.delete('new')
    const search = params.toString()
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' }, { replace: true })
    onTrigger()
  }, [action, location.pathname, location.search, navigate, onTrigger])
}
