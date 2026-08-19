import { useCallback, useMemo } from 'react'
import type { TabDef } from '../components/Tabs'
import { usePreferences } from '../features/preferences/PreferencesContext'
import { useUrlTab } from './useUrlTab'

/**
 * One page's tab row, ordered the way this user arranged it.
 *
 * Every tabbed page routes through here instead of growing its own ordering logic. The page
 * still owns *which* tabs exist (including any permission filtering it already does); this hook
 * only decides the order they appear in and which one is the default landing tab.
 *
 * Ordering rules, in this order:
 *   - saved keys first, in the user's order;
 *   - a saved key the page no longer offers is dropped — that covers both a removed tab and one
 *     the user may not see, because a hidden tab is simply absent from `tabs`. A saved order can
 *     therefore never surface something the page decided not to render;
 *   - anything the page offers that the user never ordered is appended in the page's own order,
 *     so a newly shipped tab still appears for someone with an older saved order.
 *
 * The first tab in the resulting order becomes the default landing tab, but only when the URL
 * carries no explicit `?tab=`. Deep links always win: `useUrlTab` reads the parameter first, and
 * this hook only supplies the fallback.
 */
export function useCustomisableTabs<T extends string>(
  pageKey: string,
  tabs: TabDef<T>[],
  param = 'tab',
) {
  const { preferences, setTabOrder, resetTabOrder } = usePreferences()
  const savedOrder = preferences.tab_order[pageKey]

  // Pages that derive their tab list inline (Tasks builds it from `canManage`) pass a new array
  // every render, so the memo is keyed on the tab identities, not the array reference.
  const identity = tabs.map(tab => `${tab.key}:${tab.label}:${tab.badge ?? ''}`).join('|')
  const orderedTabs = useMemo(() => {
    if (!savedOrder?.length) return tabs
    const available = new Map(tabs.map(tab => [tab.key as string, tab]))
    const ordered: TabDef<T>[] = []
    for (const key of savedOrder) {
      const tab = available.get(key)
      if (tab) { ordered.push(tab); available.delete(key) }
    }
    // Whatever the saved order did not mention keeps the page's own relative order.
    for (const tab of tabs) if (available.has(tab.key as string)) ordered.push(tab)
    return ordered
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedOrder, identity])

  const keys = useMemo(() => orderedTabs.map(tab => tab.key), [orderedTabs])
  const defaultTab = (orderedTabs[0]?.key ?? tabs[0]?.key) as T
  const [tab, setTab] = useUrlTab<T>(defaultTab, keys as readonly T[], param)

  const save = useCallback(
    (order: string[]) => setTabOrder(pageKey, order),
    [pageKey, setTabOrder],
  )
  const reset = useCallback(() => resetTabOrder(pageKey), [pageKey, resetTabOrder])
  const isCustomised = Boolean(savedOrder?.length)

  return { tab, setTab, orderedTabs, saveOrder: save, resetOrder: reset, isCustomised }
}
