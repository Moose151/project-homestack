export const OPEN_GLOBAL_SEARCH_EVENT = 'homestack-open-global-search'

/** Let a route-level phone surface open the shell-owned global Search dialog. */
export function openGlobalSearch() {
  window.dispatchEvent(new Event(OPEN_GLOBAL_SEARCH_EVENT))
}
