// Shared definition of the app's "stacks" (nav destinations) so the sidebar, Hub and
// the admin Stacks screen all agree. Accent colours mirror the --hs-accent-* CSS vars
// in index.css (keep in sync).

export interface StackDef {
  key: string        // node key, or a core-surface key
  label: string
  route: string
  icon: string
  colour: string     // accent hex
  isNode: boolean    // true → gated by the node enable/disable state; false → always-on core
}

export const STACKS: StackDef[] = [
  { key: 'hub',       label: 'Hub',       route: '/hub',       icon: '◫', colour: '#1d7a91', isNode: false },
  { key: 'calendar',  label: 'Calendar',  route: '/calendar',  icon: '📅', colour: '#2b7fd0', isNode: false },
  { key: 'atlas',     label: 'Atlas',     route: '/atlas',     icon: '🗒', colour: '#5b57d1', isNode: true },
  { key: 'meridian',  label: 'Meridian',  route: '/meridian',  icon: '⭐', colour: '#d98324', isNode: true },
  { key: 'education', label: 'Education', route: '/education', icon: '🎓', colour: '#2f9e6f', isNode: true },
  { key: 'books',     label: 'Books',     route: '/books',     icon: '📚', colour: '#8B5CF6', isNode: true },
  { key: 'home_wiki', label: 'Home Wiki', route: '/wiki',      icon: '📖', colour: '#0ca678', isNode: true },
]

export const STACK_BY_KEY: Record<string, StackDef> = Object.fromEntries(STACKS.map(s => [s.key, s]))

/** Translucent tint of an accent hex (for soft header/badge backgrounds). */
export const softColour = (hex: string, alpha = '20') => `${hex}${alpha}`
