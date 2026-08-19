import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../../api/client'
import type { UserPreferences } from '../../api/types'

/**
 * Per-user interface preferences, held once for the whole shell.
 *
 * Server-side rather than localStorage so a choice made on the desktop is already there on the
 * phone. Writes are optimistic — reordering tabs should feel instant — and reconcile against
 * the server's normalised response, which is also what rejects anything the registry does not
 * allow (apps/accounts/preferences.py).
 *
 * These values are ordering hints, never authority. Consumers intersect them with the tabs or
 * nodes the user can actually see, so a stale key for something now hidden stays hidden.
 */

const EMPTY: UserPreferences = { tab_order: {}, mobile_nav: [], sidebar_collapsed: false }

/**
 * Trust the shape, not the payload. Preferences drive navigation and the landing tab, so a
 * malformed or partial response must degrade to defaults rather than throw inside the shell and
 * take the whole app down with it.
 */
function normalise(raw: unknown): UserPreferences {
  const source = (raw ?? {}) as Partial<UserPreferences>
  const tabOrder = source.tab_order
  const mobileNav = source.mobile_nav
  return {
    tab_order: tabOrder && typeof tabOrder === 'object' && !Array.isArray(tabOrder)
      ? Object.fromEntries(
        Object.entries(tabOrder)
          .filter((entry): entry is [string, string[]] => Array.isArray(entry[1]))
          .map(([page, keys]) => [page, keys.filter(key => typeof key === 'string')]),
      )
      : {},
    mobile_nav: Array.isArray(mobileNav) ? mobileNav.filter(key => typeof key === 'string') : [],
    sidebar_collapsed: source.sidebar_collapsed === true,
  }
}

interface PreferencesCtx {
  preferences: UserPreferences
  loading: boolean
  setTabOrder: (pageKey: string, order: string[]) => Promise<void>
  resetTabOrder: (pageKey: string) => Promise<void>
  setMobileNav: (keys: string[]) => Promise<void>
  resetMobileNav: () => Promise<void>
  setSidebarCollapsed: (collapsed: boolean) => Promise<void>
}

const Ctx = createContext<PreferencesCtx>({
  preferences: EMPTY,
  loading: true,
  setTabOrder: async () => {},
  resetTabOrder: async () => {},
  setMobileNav: async () => {},
  resetMobileNav: async () => {},
  setSidebarCollapsed: async () => {},
})

/** The pre-server key the mobile dock used, migrated once then removed. */
const legacyMobileNavKeys = (userId: number | string) => [
  `hs-mobile-nav-${userId}`,
  'hs-mobile-nav',
]

export function PreferencesProvider({ userId, children }: { userId: number | null; children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(EMPTY)
  const [loading, setLoading] = useState(true)
  const migrated = useRef<string | null>(null)

  useEffect(() => {
    if (userId == null) { setPreferences(EMPTY); setLoading(false); return }
    let cancelled = false
    setLoading(true)
    api.getUserPreferences()
      .then(async raw => {
        if (cancelled) return
        let loaded = normalise(raw)
        // One-time migration of the browser-only dock preference, mirroring the guide-dismissal
        // migration: adopt it only when the account has no server choice yet, so a value from
        // an old phone can never overwrite a deliberate later one.
        const keys = legacyMobileNavKeys(userId)
        const legacyRaw = keys.map(key => localStorage.getItem(key)).find(Boolean)
        if (legacyRaw && !loaded.mobile_nav.length && migrated.current !== String(userId)) {
          migrated.current = String(userId)
          try {
            const parsed = JSON.parse(legacyRaw)
            const slots = Array.isArray(parsed)
              ? parsed.filter((key): key is string => typeof key === 'string').slice(0, 2)
              : []
            if (slots.length) loaded = normalise(await api.updateUserPreferences({ mobile_nav: slots }))
          } catch { /* an unreadable legacy value is simply dropped */ }
        }
        if (legacyRaw) keys.forEach(key => localStorage.removeItem(key))
        if (!cancelled) setPreferences(loaded)
      })
      .catch(() => { if (!cancelled) setPreferences(EMPTY) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [userId])

  // Optimistic write with rollback: the interface should respond immediately, but the server's
  // normalised value wins, and a failed write must not leave a lie on screen.
  const commit = useCallback(async (optimistic: UserPreferences, patch: Partial<UserPreferences>) => {
    const previous = preferences
    setPreferences(optimistic)
    try {
      setPreferences(normalise(await api.updateUserPreferences(patch)))
    } catch {
      setPreferences(previous)
    }
  }, [preferences])

  const setTabOrder = useCallback(async (pageKey: string, order: string[]) => {
    await commit(
      { ...preferences, tab_order: { ...preferences.tab_order, [pageKey]: order } },
      { tab_order: { [pageKey]: order } },
    )
  }, [commit, preferences])

  const resetTabOrder = useCallback(async (pageKey: string) => {
    const next = { ...preferences.tab_order }
    delete next[pageKey]
    // An empty list is the reset signal the API understands for a single page.
    await commit({ ...preferences, tab_order: next }, { tab_order: { [pageKey]: [] } })
  }, [commit, preferences])

  const setMobileNav = useCallback(async (keys: string[]) => {
    await commit({ ...preferences, mobile_nav: keys }, { mobile_nav: keys })
  }, [commit, preferences])

  const setSidebarCollapsed = useCallback(async (collapsed: boolean) => {
    await commit(
      { ...preferences, sidebar_collapsed: collapsed },
      { sidebar_collapsed: collapsed },
    )
  }, [commit, preferences])

  const resetMobileNav = useCallback(async () => {
    const previous = preferences
    setPreferences({ ...preferences, mobile_nav: [] })
    try {
      setPreferences(normalise(await api.resetUserPreferences('mobile_nav')))
    } catch {
      setPreferences(previous)
    }
  }, [preferences])

  return (
    <Ctx.Provider value={{
      preferences, loading, setTabOrder, resetTabOrder, setMobileNav, resetMobileNav,
      setSidebarCollapsed,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const usePreferences = () => useContext(Ctx)
