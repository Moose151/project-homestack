// Shared definition of the app's "stacks" (nav destinations) so the sidebar, Hub and
// the admin Stacks screen all agree. Accent colours mirror the --hs-accent-* CSS vars
// in index.css (keep in sync).

export interface StackDef {
  key: string        // node key, or a core-surface key
  label: string
  navLabel: string   // plain-language destination name used in global navigation
  shortLabel: string // compact phone bottom-bar label
  description: string
  navGroup: 'start' | 'organise' | 'household' | 'money'
  route: string
  icon: string
  colour: string     // accent hex
  isNode: boolean    // true → gated by the node enable/disable state; false → always-on core
}

export const STACKS: StackDef[] = [
  { key: 'hub', label: 'Home', navLabel: 'Home', shortLabel: 'Home', description: 'Your household at a glance', navGroup: 'start', route: '/hub', icon: '🏡', colour: '#1d7a91', isNode: false },
  { key: 'calendar', label: 'Calendar', navLabel: 'Calendar', shortLabel: 'Calendar', description: 'Events, care and schedules', navGroup: 'start', route: '/calendar', icon: '📅', colour: '#2b7fd0', isNode: false },
  { key: 'atlas', label: 'Atlas', navLabel: 'Lists & notes', shortLabel: 'Lists', description: 'To-dos, reminders and notes', navGroup: 'organise', route: '/atlas', icon: '🗒', colour: '#5b57d1', isNode: true },
  { key: 'education', label: 'Education', navLabel: 'School & study', shortLabel: 'Study', description: 'Classes, work and deadlines', navGroup: 'organise', route: '/education', icon: '🎓', colour: '#2f9e6f', isNode: true },
  { key: 'books', label: 'Books', navLabel: 'Books', shortLabel: 'Books', description: 'Reading, clubs and wishlists', navGroup: 'organise', route: '/books', icon: '📚', colour: '#8B5CF6', isNode: true },
  { key: 'home_wiki', label: 'Home Wiki', navLabel: 'Household guide', shortLabel: 'Guide', description: 'Useful shared information', navGroup: 'organise', route: '/wiki', icon: '📖', colour: '#0ca678', isNode: true },
  { key: 'pets', label: 'Pets', navLabel: 'Pets', shortLabel: 'Pets', description: 'Care, treatments and appointments', navGroup: 'household', route: '/pets', icon: '🐾', colour: '#d9642c', isNode: true },
  { key: 'homestead', label: 'Homestead', navLabel: 'Our home', shortLabel: 'Our home', description: 'Rooms, upkeep and services', navGroup: 'household', route: '/homestead', icon: '🏠', colour: '#b0563c', isNode: true },
  { key: 'meridian', label: 'Meridian', navLabel: 'Tasks & rewards', shortLabel: 'Tasks', description: 'Family jobs, points and goals', navGroup: 'household', route: '/meridian', icon: '⭐', colour: '#d98324', isNode: true },
  { key: 'solace', label: 'Solace', navLabel: 'Money', shortLabel: 'Money', description: 'Bills, pay cycles and plans', navGroup: 'money', route: '/solace', icon: '💸', colour: '#8f4e38', isNode: true },
]

export const STACK_BY_KEY: Record<string, StackDef> = Object.fromEntries(STACKS.map(s => [s.key, s]))

/** Translucent tint of an accent hex (for soft header/badge backgrounds). */
export const softColour = (hex: string, alpha = '20') => `${hex}${alpha}`
