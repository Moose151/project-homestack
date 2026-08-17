import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { CSSProperties, Dispatch, SetStateAction } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { NotificationBell } from '../../components/NotificationBell'
import { CalendarPeek } from '../../components/CalendarPeek'
import { Logo } from '../../components/Logo'
import { useDarkMode } from '../../hooks/useDarkMode'
import { useDialogA11y } from '../../components/useDialogA11y'
import { useStacks } from '../stacks/StacksContext'
import { STACKS, softColour } from '../../config/stacks'
import { APP_VERSION } from '../../config/version'
import { api } from '../../api/client'
import type { AuthUser } from '../../api/types'
import { DialogHost } from '../../components/Dialogs'
import { ConnectionBanner } from '../../components/ConnectionBanner'
import { CONTENT_CONTAINER } from '../../components/PageContainer'
import { GlobalSearch } from '../../components/GlobalSearch'
import { QuickCreate } from '../../components/QuickCreate'
import { useScrollRestoration } from '../../hooks/useScrollRestoration'
import { InlineAlert } from '../../components/PageState'
import { ColourPicker } from '../../components/ColourPicker'
import { OPEN_GLOBAL_SEARCH_EVENT } from '../../lib/shellEvents'

interface NavItem {
  key: string
  label: string
  shortLabel: string
  description: string
  group: 'start' | 'organise' | 'household' | 'money' | 'manage'
  route: string
  icon: string
  colour: string
}

const GUIDE_VERSION = '1'

const NAV_GROUPS: Array<{ key: NavItem['group']; label: string }> = [
  { key: 'start', label: 'Start here' },
  { key: 'organise', label: 'Plan & organise' },
  { key: 'household', label: 'Household' },
  { key: 'money', label: 'Money' },
]

// Mobile bottom bar (docs/36_Mobile_UX_Strategy_and_Implementation_Plan.md §4.2): Home, Add and
// More are fixed; only the two remaining slots are user-configurable shortcuts. Calendar is the
// default first shortcut for most households.
const MOBILE_SHORTCUT_SLOTS = 2
const MOBILE_DEFAULT_SHORTCUT_PRIORITY = [
  'calendar', 'atlas', 'meridian', 'homestead', 'pets',
  'education', 'home_wiki', 'solace', 'fitness', 'books', 'travel',
]

const EMOJI_OPTS = ['🐱','🐶','🦊','🐼','🐻','🦋','🦄','🐸','🐳','🌻','🌙','⭐','🎸','🎮','🏄','🍕','🎩','🔮','🌈','🦅']

// The search shortcut is Cmd on Apple hardware and Ctrl everywhere else. Showing "⌘K" to a
// Linux or Windows household advertises a key they do not have.
const SHORTCUT_MODIFIER = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
  ? '⌘'
  : 'Ctrl '

function ProfileEditor({ user, onSaved, onClose }: {
  user: AuthUser
  onSaved: (u: AuthUser) => void
  onClose: () => void
}) {
  const [name, setName] = useState(user.display_name)
  const [colour, setColour] = useState(user.colour || '#4A90E2')
  const [avatar, setAvatar] = useState(user.avatar || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    if (!name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const updated = await api.patchMe({ display_name: name.trim(), colour, avatar })
      onSaved(updated)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally { setBusy(false) }
  }

  const inputCls = 'w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-primary/40'

  return (
    <div className="bg-sunken rounded-2xl p-3 space-y-3 border border-line">
      <div className="text-xs font-semibold text-muted-strong uppercase tracking-wide">Edit profile</div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <input
        className={inputCls}
        value={name}
        onChange={e => setName(e.target.value)}
        placeholder="Your name"
      />
      <div className="space-y-2">
        <span className="text-xs font-semibold text-muted-strong">Accent colour</span>
        <ColourPicker value={colour} onChange={setColour} ariaLabel="Profile accent colour" />
        <div className="flex justify-end">
        <Avatar name={name || '?'} colour={colour} avatar={avatar} size="md" />
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {EMOJI_OPTS.map(e => (
          <button
            key={e}
            onClick={() => setAvatar(avatar === e ? '' : e)}
            className={`w-8 h-8 rounded-lg text-lg transition-all ${avatar === e ? 'ring-2 ring-primary bg-primary/10' : 'hover:bg-surface'}`}
          >{e}</button>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={save}
          disabled={busy || !name.trim()}
          className="px-3 py-1.5 rounded-xl bg-primary text-white text-xs font-semibold disabled:opacity-50"
        >{busy ? 'Saving…' : 'Save'}</button>
        <button onClick={onClose} className="px-3 py-1.5 rounded-xl text-xs text-muted hover:text-ink">Cancel</button>
      </div>
      <Link to="/settings/notifications" className="block text-xs font-bold text-primary hover:underline">
        🔔 Notification settings →
      </Link>
    </div>
  )
}

/** A descriptive sidebar destination. Internal node names stay out of the way here. */
function SidebarLink({ item, accent }: { item: NavItem; accent: boolean }) {
  const activeStyle = ({ isActive }: { isActive: boolean }): CSSProperties | undefined =>
    isActive && accent ? { background: softColour(item.colour, '18'), color: item.colour } : undefined
  return (
    <NavLink
      to={item.route}
      style={activeStyle}
      className={({ isActive }) =>
        `group relative flex min-h-[52px] items-center gap-3 rounded-xl px-2.5 py-2 transition-all ${
          isActive ? (accent ? '' : 'bg-sunken text-ink') : 'text-muted-strong hover:bg-sunken/80'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {/* Absolutely positioned so the label box is the same width active or not —
              otherwise the description truncates only on the current page and text jitters
              as you navigate. On the left, where it reads as an indicator not a scrollbar. */}
          {isActive && (
            <span
              className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full"
              style={{ backgroundColor: accent ? item.colour : 'var(--hs-primary)' }}
              aria-hidden
            />
          )}
          <span
            className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl text-lg transition-transform group-hover:scale-105"
            style={{ background: softColour(item.colour, isActive ? '25' : '12') }}
          >
            {item.icon}
          </span>
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm font-bold">{item.label}</span>
            <span className={`mt-0.5 block truncate text-[10px] font-medium ${isActive ? 'opacity-75' : 'text-muted'}`}>{item.description}</span>
          </span>
        </>
      )}
    </NavLink>
  )
}

/** One tappable destination in the mobile bottom bar — Home or a configurable shortcut. */
function MobileNavLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.route}
      style={({ isActive }) => (isActive ? { color: item.colour, background: softColour(item.colour, '14') } : undefined)}
      className={({ isActive }) =>
        `group flex min-h-11 min-w-0 flex-col items-center justify-center rounded-[1.15rem] px-0.5 py-1 text-[10px] font-extrabold transition-[background-color,color,transform] duration-150 active:scale-[0.96] motion-reduce:transform-none motion-reduce:transition-none ${
          isActive ? '' : 'text-muted'
        }`
      }
      data-nav-key={item.key}
    >
      {({ isActive }) => (
        <>
          <span
            className="grid h-7 min-w-10 place-items-center rounded-full px-2 text-[19px] leading-none transition-transform duration-150 group-active:scale-95 motion-reduce:transform-none motion-reduce:transition-none"
            style={{ background: isActive ? softColour(item.colour, '24') : 'transparent' }}
          >
            {item.icon}
          </span>
          <span className="mt-0.5 max-w-full truncate px-0.5 leading-3">{item.shortLabel}</span>
        </>
      )}
    </NavLink>
  )
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="px-3 pb-1 pt-3 text-[10px] font-extrabold uppercase tracking-[0.15em] text-muted/60 select-none">
      {children}
    </p>
  )
}

/**
 * Mobile destination directory + profile/preferences. A separate component (not inline JSX
 * gated by `{moreOpen && ...}`) so it can call `useDialogA11y` itself, matching every other
 * sheet in the app (Modal, and anything built on it) — the hook's mount/unmount lifecycle
 * needs the sheet to actually mount/unmount, not just toggle visibility inside an
 * always-mounted parent, since React hooks can't be called conditionally.
 */
function MoreSheet({
  user, editingProfile, setEditingProfile, updateUser, stackNav, customisingNav, setCustomisingNav,
  effectiveMobileKeys, setMobileSlot, resetMobileKeys, adminNav, dark, setDark, onSearch, logout, onClose,
}: {
  user: AuthUser | null
  editingProfile: boolean
  setEditingProfile: Dispatch<SetStateAction<boolean>>
  updateUser: (u: AuthUser) => void
  stackNav: NavItem[]
  customisingNav: boolean
  setCustomisingNav: Dispatch<SetStateAction<boolean>>
  effectiveMobileKeys: string[]
  setMobileSlot: (slot: number, key: string) => void
  resetMobileKeys: () => void
  adminNav: NavItem[]
  dark: boolean
  setDark: (v: boolean) => void
  onSearch: () => void
  logout: () => void
  onClose: () => void
}) {
  const dialogRef = useDialogA11y(onClose)
  const shortcutOptions = stackNav.filter(item => item.key !== 'hub')
  const pinnedItems = effectiveMobileKeys
    .map(key => stackNav.find(item => item.key === key))
    .filter((item): item is NavItem => Boolean(item))

  return (
    <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="All HomeStack">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" onClick={onClose} />
      <div
        ref={dialogRef}
        className="absolute inset-x-0 bottom-0 max-h-[90vh] overflow-y-auto rounded-t-[2rem] border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] shadow-card"
      >
        <div className="sticky top-0 z-10 border-b border-line bg-surface/95 px-5 pb-3 pt-2 backdrop-blur-xl">
          <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line-strong" />
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-extrabold text-ink">All HomeStack</h2>
              <p className="text-xs text-muted">Find any area, setting or account action</p>
            </div>
            <button onClick={onClose} className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-sunken" aria-label="Close">✕</button>
          </div>
        </div>

        <div className="space-y-5 p-4">
          <button
            onClick={() => { onClose(); onSearch() }}
            className="flex min-h-14 w-full items-center gap-3 rounded-2xl border border-line bg-sunken/70 px-4 text-left text-sm font-bold text-ink shadow-soft transition-transform active:scale-[0.98] motion-reduce:transform-none"
            aria-label="Search all HomeStack"
          >
            <span className="text-xl" aria-hidden>⌕</span>
            <span className="flex-1">Search all HomeStack</span>
            <span className="text-xs font-semibold text-muted">{SHORTCUT_MODIFIER}K</span>
          </button>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3 px-1">
              <span>
                <span className="block text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">Pinned</span>
                <span className="mt-0.5 block text-[11px] text-muted">Your two bottom-bar shortcuts</span>
              </span>
              <button onClick={() => setCustomisingNav(value => !value)} className="min-h-11 rounded-lg px-2 text-xs font-bold text-primary hover:bg-primary-soft">
                {customisingNav ? 'Done' : 'Edit shortcuts'}
              </button>
            </div>
            {customisingNav ? (
              <div className="space-y-2 rounded-2xl border border-line bg-sunken/45 p-2.5">
                {[0, 1].map(slot => {
                  const item = pinnedItems[slot]
                  return (
                    <label key={slot} className="flex min-h-[68px] items-center gap-2.5 rounded-xl bg-surface px-3 py-2 shadow-sm">
                      <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl text-xl" style={{ background: item ? softColour(item.colour, '18') : 'var(--hs-primary-soft)' }}>
                        {item?.icon ?? '◇'}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[10px] font-extrabold uppercase tracking-wide text-muted">Slot {slot + 1}</span>
                        <span className="block truncate text-sm font-bold text-ink">{item?.label ?? 'Choose a shortcut'}</span>
                      </span>
                      <span className="relative flex-shrink-0">
                        <span className="pointer-events-none absolute inset-y-0 left-2 flex items-center text-[11px] font-bold text-primary">Change</span>
                        <select
                          value={item?.key ?? ''}
                          onChange={event => setMobileSlot(slot, event.target.value)}
                          aria-label={`Choose shortcut for Slot ${slot + 1}`}
                          className="h-11 w-[5.5rem] appearance-none rounded-xl border border-line bg-surface pl-2 pr-6 text-transparent outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
                        >
                          {shortcutOptions.map(option => <option key={option.key} value={option.key} className="text-ink">{option.label}</option>)}
                        </select>
                        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted">⌄</span>
                      </span>
                    </label>
                  )
                })}
                <button type="button" onClick={resetMobileKeys} className="min-h-11 w-full rounded-xl px-3 text-xs font-bold text-muted-strong hover:bg-surface hover:text-primary">
                  Reset to recommended
                </button>
                <p className="px-1 text-[11px] leading-4 text-muted">Home, Add and More stay fixed. Choosing the other pinned area swaps the two slots, so duplicates are never created.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {pinnedItems.map(item => (
                  <NavLink
                    key={item.route}
                    to={item.route}
                    onClick={onClose}
                    style={({ isActive }) => (isActive ? { borderColor: item.colour, background: softColour(item.colour, '14'), color: item.colour } : undefined)}
                    className={({ isActive }) => `flex min-h-[64px] items-center gap-2 rounded-2xl border p-2.5 text-left transition-transform active:scale-[0.98] motion-reduce:transform-none ${isActive ? 'shadow-sm' : 'border-line bg-surface text-muted-strong'}`}
                  >
                    <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl text-xl" style={{ background: softColour(item.colour, '18') }}>{item.icon}</span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-extrabold">{item.label}</span>
                      <span className="mt-0.5 block text-[11px] opacity-70">Pinned</span>
                    </span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">All areas</p>
            <div className="space-y-3">
              {NAV_GROUPS.map(group => {
                const items = stackNav.filter(item => item.group === group.key)
                if (items.length === 0) return null
                return (
                  <section key={group.key} aria-labelledby={`more-${group.key}`}>
                    <h3 id={`more-${group.key}`} className="mb-1.5 px-1 text-xs font-bold text-muted-strong">{group.label}</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {items.map(item => (
                        <NavLink
                          key={item.route}
                          to={item.route}
                          onClick={onClose}
                          style={({ isActive }) => (isActive ? { borderColor: item.colour, background: softColour(item.colour, '14'), color: item.colour } : undefined)}
                          className={({ isActive }) => `flex min-h-[72px] items-center gap-2 rounded-2xl border p-2.5 text-left transition-transform active:scale-[0.98] motion-reduce:transform-none ${isActive ? 'shadow-sm' : 'border-line bg-surface text-muted-strong'}`}
                        >
                          <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl text-xl" style={{ background: softColour(item.colour, '18') }}>{item.icon}</span>
                          <span className="min-w-0">
                            <span className="block text-sm font-extrabold leading-tight">{item.label}</span>
                            <span className="mt-0.5 line-clamp-2 text-[10px] leading-tight opacity-70">{item.description}</span>
                          </span>
                        </NavLink>
                      ))}
                    </div>
                  </section>
                )
              })}
            </div>
          </div>

          <div>
            <p className="mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">Account & app</p>
            {user && (
              <div className="mb-2 rounded-2xl border border-line p-3" style={{ background: `linear-gradient(135deg, ${softColour(user.colour || '#1d7a91', '18')}, var(--hs-surface) 68%)` }}>
                <div className="flex items-center gap-3">
                  <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="md" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-extrabold text-ink">{user.display_name}</p>
                    <p className="text-xs font-semibold capitalize text-muted">{user.role} profile</p>
                  </div>
                  <button onClick={() => setEditingProfile(value => !value)} className="min-h-11 rounded-xl border border-line bg-surface/80 px-3 py-2 text-xs font-bold text-primary shadow-sm">
                    {editingProfile ? 'Done' : 'Edit'}
                  </button>
                </div>
                {editingProfile && (
                  <div className="mt-3">
                    <ProfileEditor user={user} onSaved={u => { updateUser(u); setEditingProfile(false) }} onClose={() => setEditingProfile(false)} />
                  </div>
                )}
              </div>
            )}
            <div className="overflow-hidden rounded-2xl border border-line bg-surface">
              <NavLink to="/settings/notifications" onClick={onClose} className="flex min-h-12 items-center gap-3 border-b border-line px-3 text-sm font-semibold text-muted-strong hover:bg-sunken">
                <span className="w-6 text-center text-lg">🔔</span>
                Notifications
              </NavLink>
              <button
                onClick={() => setDark(!dark)}
                className="flex min-h-12 w-full items-center gap-3 border-b border-line px-3 text-left text-sm font-semibold text-muted-strong hover:bg-sunken"
              >
                <span className="text-lg w-6 text-center">{dark ? '☀' : '☾'}</span>
                Appearance · {dark ? 'Use light mode' : 'Use dark mode'}
              </button>
              {adminNav.map(item => (
                <NavLink key={item.route} to={item.route} onClick={onClose} className="flex min-h-12 items-center gap-3 border-b border-line px-3 text-sm font-semibold text-muted-strong hover:bg-sunken">
                  <span className="w-6 text-center text-lg">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
              <a
                href="/kiosk"
                className="flex min-h-12 items-center gap-3 border-b border-line px-3 text-sm font-semibold text-muted-strong hover:bg-sunken"
              >
                <span className="text-lg w-6 text-center">▣</span>
                Enter kiosk
              </a>
              {user && (
                <button
                  onClick={() => { onClose(); logout() }}
                  className="flex min-h-12 w-full items-center gap-3 px-3 text-left text-sm font-semibold text-muted-strong hover:bg-danger-soft hover:text-danger"
                >
                  <span className="text-lg w-6 text-center">⊗</span>
                  Sign out
                </button>
              )}
            </div>
          </div>

          <p className="border-t border-line px-1 pt-4 text-center text-[10px] font-medium text-muted/45">HomeStack v{APP_VERSION}</p>
        </div>
      </div>
    </div>
  )
}

export function AppShell() {
  const { user, logout, updateUser } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  // React Router assigns a fresh `key` to every entry it pushes/replaces, and the very first
  // entry of a session (cold load, PWA launch, a push-notification/deep link opened straight
  // into a nested route) always keys as "default". Capturing that once at mount and comparing
  // against the *current* key — not a boolean ref flipped by an effect — tells us, on every
  // render, whether the user has actually navigated in-app since landing here. `navigate(-1)`
  // on a cold entry would leave HomeStack (or land on an unrelated prior browser-history page);
  // falling back to the stack's own base route keeps Back inside the app.
  const initialLocationKey = useRef(location.key).current
  const hasInAppHistory = location.key !== initialLocationKey
  const [dark, setDark] = useDarkMode()
  const [editingProfile, setEditingProfile] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [customisingNav, setCustomisingNav] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const mobileNavStorageKey = `hs-mobile-nav-${user?.id ?? 'guest'}`
  const [hiddenGuides, setHiddenGuides] = useState<string[]>([])
  const [mobileKeys, setMobileKeys] = useState<string[]>(() => {
    try {
      // Read the former household-global preference once as a migration seed. After the stack
      // permissions load, the repair effect below moves it to this user's scoped key.
      const stored = localStorage.getItem(`hs-mobile-nav-${user?.id ?? 'guest'}`)
        ?? localStorage.getItem('hs-mobile-nav')
      const saved = JSON.parse(stored || '[]')
      return Array.isArray(saved) ? saved.filter((key): key is string => typeof key === 'string') : []
    } catch {
      return []
    }
  })
  const hasCustomizedNav = useRef(
    localStorage.getItem(`hs-mobile-nav-${user?.id ?? 'guest'}`) !== null
      || localStorage.getItem('hs-mobile-nav') !== null,
  )
  const { enabledKeys, loading: stacksLoading, error: stacksError, refresh: refreshStacks } = useStacks()
  useScrollRestoration()

  // Core surfaces (Hub, Calendar) always show; node-backed stacks only when enabled.
  const coreNav: NavItem[] = STACKS
    .filter(s => !s.isNode)
    .map(s => ({ key: s.key, label: s.navLabel, shortLabel: s.shortLabel, description: s.description, group: s.navGroup, route: s.route, icon: s.icon, colour: s.colour }))
  const nodeNav: NavItem[] = STACKS
    .filter(s => s.isNode && enabledKeys.has(s.key))
    .map(s => ({ key: s.key, label: s.navLabel, shortLabel: s.shortLabel, description: s.description, group: s.navGroup, route: s.route, icon: s.icon, colour: s.colour }))
  const stackNav: NavItem[] = [...coreNav, ...nodeNav]

  const adminNav: NavItem[] = user?.role === 'admin'
      ? [
        { key: 'users', label: 'People & access', shortLabel: 'People', description: 'Profiles, roles and sign-in', group: 'manage', route: '/users', icon: '👥', colour: '#64748b' },
        { key: 'settings', label: 'Manage HomeStack', shortLabel: 'Manage', description: 'Stacks and household settings', group: 'manage', route: '/settings', icon: '⚙️', colour: '#64748b' },
      ]
    : []

  // Mobile bottom bar: Home, Add and More are fixed; two remaining slots are configurable
  // shortcuts (docs/36 §4.2). Everything else lives behind the "More" sheet.
  const availableKeys = new Set(stackNav.map(item => item.key))
  const hubItem = stackNav.find(item => item.key === 'hub')
  const recommendedPool = Array.from(new Set([
    ...MOBILE_DEFAULT_SHORTCUT_PRIORITY,
    ...stackNav.map(item => item.key),
  ])).filter(key => key !== 'hub' && availableKeys.has(key))
  const defaultMobileKeys = recommendedPool.slice(0, MOBILE_SHORTCUT_SLOTS)
  // The dock always has two configurable positions. Missing, duplicated, disabled or newly
  // inaccessible saved choices are repaired from the documented priority, without replacing
  // any still-valid explicit choice.
  const rawSavedKeys = mobileKeys.filter(key => key !== 'hub').slice(0, MOBILE_SHORTCUT_SLOTS)
  const effectiveMobileKeys = hasCustomizedNav.current
    ? (() => {
      const reserved = new Set(rawSavedKeys.filter(key => availableKeys.has(key)))
      const used = new Set<string>()
      return Array.from({ length: MOBILE_SHORTCUT_SLOTS }, (_, slot) => {
        const saved = rawSavedKeys[slot]
        if (saved && availableKeys.has(saved) && !used.has(saved)) {
          used.add(saved)
          return saved
        }
        const replacement = recommendedPool.find(key => !used.has(key) && !reserved.has(key))
          ?? recommendedPool.find(key => !used.has(key))
        if (replacement) used.add(replacement)
        return replacement
      }).filter((key): key is string => Boolean(key))
    })()
    : defaultMobileKeys
  const mobileKeysSignature = JSON.stringify(mobileKeys)
  const effectiveMobileKeysSignature = JSON.stringify(effectiveMobileKeys)
  const mobileShortcuts = effectiveMobileKeys
    .map(key => stackNav.find(item => item.key === key))
    .filter((item): item is NavItem => Boolean(item))
  const currentNav = [...stackNav, ...adminNav].find(item => location.pathname.startsWith(item.route))
  const hasOwnMobileSlot = currentNav && (currentNav.key === 'hub' || mobileShortcuts.some(item => item.key === currentNav.key))
  // More never changes identity. It only takes a subtle active treatment when the current area
  // is reached through the launcher rather than owning one of the two shortcut slots.
  const currentIsInMore = Boolean(!hasOwnMobileSlot && location.pathname !== '/')
  // Mobile-only: the top bar shows Back instead of the destination icon once you're inside a
  // subscreen (docs/36 §4.1) — a route nested below the matched stack's own base route.
  const isNestedRoute = Boolean(currentNav && location.pathname !== currentNav.route)
  const goBack = () => {
    if (hasInAppHistory) navigate(-1)
    else navigate(currentNav?.route ?? '/hub')
  }
  const contextualGuide = currentNav && !['settings', 'users'].includes(currentNav.key) && !hiddenGuides.includes(currentNav.key)
    ? currentNav
    : null

  const hideContextualGuide = (key: string) => {
    setHiddenGuides(previous => Array.from(new Set([...previous, key])))
    api.dismissGuide(key, GUIDE_VERSION).catch(() => {
      setHiddenGuides(previous => previous.filter(identifier => identifier !== key))
    })
  }

  const persistMobileKeys = (keys: string[]) => {
    hasCustomizedNav.current = true
    localStorage.setItem(mobileNavStorageKey, JSON.stringify(keys))
    setMobileKeys(keys)
  }

  const setMobileSlot = (slot: number, key: string) => {
    if (key === 'hub' || !availableKeys.has(key) || slot < 0 || slot >= MOBILE_SHORTCUT_SLOTS) return
    const next = [...effectiveMobileKeys]
    const otherSlot = next.indexOf(key)
    if (otherSlot !== -1 && otherSlot !== slot) next[otherSlot] = next[slot]
    next[slot] = key
    persistMobileKeys(next)
  }

  const resetMobileKeys = () => {
    hasCustomizedNav.current = false
    localStorage.removeItem(mobileNavStorageKey)
    // Remove the legacy global setting too, otherwise it would immediately reseed this user.
    localStorage.removeItem('hs-mobile-nav')
    setMobileKeys([])
  }

  useEffect(() => {
    if (stacksLoading || !hasCustomizedNav.current) return
    const migratingLegacyPreference = localStorage.getItem(mobileNavStorageKey) === null
      && localStorage.getItem('hs-mobile-nav') !== null
    if (mobileKeysSignature === effectiveMobileKeysSignature && !migratingLegacyPreference) return
    localStorage.setItem(mobileNavStorageKey, effectiveMobileKeysSignature)
    if (migratingLegacyPreference) localStorage.removeItem('hs-mobile-nav')
    if (mobileKeysSignature !== effectiveMobileKeysSignature) setMobileKeys(JSON.parse(effectiveMobileKeysSignature))
  }, [stacksLoading, mobileNavStorageKey, effectiveMobileKeysSignature, mobileKeysSignature])

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname, location.search])

  useEffect(() => {
    if (!user) { setHiddenGuides([]); return }
    const legacyKey = `hs-hidden-guides-${user.id}`
    const reload = async () => {
      try {
        const rows = await api.getGuideDismissals()
        const serverKeys = rows
          .filter(row => row.guide_version === GUIDE_VERSION)
          .map(row => row.guide_identifier)
        let legacyKeys: string[] = []
        try {
          const saved = JSON.parse(localStorage.getItem(legacyKey) || '[]')
          legacyKeys = Array.isArray(saved) ? saved.filter((key): key is string => typeof key === 'string') : []
        } catch { legacyKeys = [] }
        const missing = legacyKeys.filter(key => !serverKeys.includes(key))
        if (missing.length) await Promise.all(missing.map(key => api.dismissGuide(key, GUIDE_VERSION)))
        localStorage.removeItem(legacyKey)
        setHiddenGuides(Array.from(new Set([...serverKeys, ...missing])))
      } catch {
        setHiddenGuides([])
      }
    }
    void reload()
    window.addEventListener('homestack-guide-preferences', reload)
    return () => window.removeEventListener('homestack-guide-preferences', reload)
  }, [user])

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    const openSearch = () => setSearchOpen(true)
    window.addEventListener('keydown', shortcut)
    window.addEventListener(OPEN_GLOBAL_SEARCH_EVENT, openSearch)
    return () => {
      window.removeEventListener('keydown', shortcut)
      window.removeEventListener(OPEN_GLOBAL_SEARCH_EVENT, openSearch)
    }
  }, [])

  return (
    <div className="min-h-screen flex">
      {/* Sidebar — md+ */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[272px] flex-col border-r border-line bg-surface/92 backdrop-blur-xl md:flex">
        {/* Height and padding match the main header exactly so the two bottom borders and the
            two title baselines line up across the sidebar seam. */}
        <NavLink
          to="/hub"
          className="flex h-[62px] flex-shrink-0 items-center gap-3 border-b border-line px-3 transition-colors hover:bg-sunken/60 md:h-[68px] md:px-6"
          aria-label="HomeStack home"
        >
          <Logo className="h-9 w-9 flex-shrink-0" />
          <span className="min-w-0">
            <span className="block truncate text-base font-extrabold tracking-tight text-ink">HomeStack</span>
            <span className="block truncate text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Our household</span>
          </span>
        </NavLink>

        {/* The mask fades the last row when the list overflows, so a half-visible destination
            reads as "scroll for more" instead of a clipped layout. */}
        <nav
          className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-2 [mask-image:linear-gradient(to_bottom,black_calc(100%-1.5rem),transparent)]"
        >
          {NAV_GROUPS.map(group => {
            const items = stackNav.filter(item => item.group === group.key)
            if (items.length === 0) return null
            return (
              <div key={group.key}>
                <SectionLabel>{group.label}</SectionLabel>
                {items.map(item => <SidebarLink key={item.route} item={item} accent />)}
              </div>
            )
          })}

          {adminNav.length > 0 && (
            <>
              <SectionLabel>Manage</SectionLabel>
              {adminNav.map(item => <SidebarLink key={item.route} item={item} accent={false} />)}
            </>
          )}
        </nav>

        <div className="flex flex-col gap-2 border-t border-line bg-sunken/25 px-3 py-3">
          <div className="grid grid-cols-2 gap-1">
            <button
              onClick={() => setDark(!dark)}
              className="flex min-h-10 items-center justify-center gap-1.5 rounded-xl text-xs font-semibold text-muted hover:bg-surface hover:text-ink"
            >
              {dark ? '☀ Light' : '☾ Dark'}
            </button>
            <a
              href="/kiosk"
              className="flex min-h-10 items-center justify-center gap-1.5 rounded-xl text-xs font-semibold text-muted hover:bg-surface hover:text-ink"
            >
              <span>▣</span> Kiosk
            </a>
          </div>
          {user && (
            <>
              <div className="flex items-center gap-2 rounded-2xl border border-line bg-surface p-2.5 shadow-soft">
                <button onClick={() => setEditingProfile(v => !v)} className="flex-shrink-0 rounded-full" title="Edit profile">
                  <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="sm" />
                </button>
                <div className="flex-1 min-w-0">
                  <button onClick={() => setEditingProfile(v => !v)} className="text-left w-full">
                    <p className="truncate text-sm font-bold text-ink transition-colors hover:text-primary">{user.display_name}</p>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">{user.role}</p>
                  </button>
                </div>
                <button
                  onClick={logout}
                  className="grid h-9 w-9 place-items-center rounded-xl text-sm text-muted transition-colors hover:bg-danger-soft hover:text-danger"
                  title="Sign out"
                  aria-label="Sign out"
                >
                  ↪
                </button>
              </div>
              {editingProfile && (
                <ProfileEditor
                  user={user}
                  onSaved={u => { updateUser(u); setEditingProfile(false) }}
                  onClose={() => setEditingProfile(false)}
                />
              )}
            </>
          )}
          <p className="select-none text-center text-[9px] font-semibold tracking-wider text-muted/40">v{APP_VERSION}</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex min-h-screen min-w-0 flex-1 flex-col md:ml-[272px]">
        <header className="sticky top-0 z-10 h-[62px] border-b border-line bg-surface/82 backdrop-blur-xl md:h-[68px]">
          <div className={`${CONTENT_CONTAINER} flex h-full items-center gap-1.5`}>
          <div className="mr-auto flex min-w-0 items-center gap-2.5">
            {/* Mobile-only Back, replacing the destination icon once inside a subscreen
                (docs/36 §4.1) — a simplified top bar leaves Search/Create to the bottom nav
                and More sheet on phone; desktop keeps its full top bar unchanged (§8 Phase 3). */}
            {isNestedRoute && (
              <button
                onClick={goBack}
                aria-label="Back"
                className="-ml-1.5 grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-2xl text-muted transition-colors hover:bg-sunken hover:text-ink md:hidden"
              >
                ‹
              </button>
            )}
            <span
              className={`inline-grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl text-lg shadow-sm ${isNestedRoute ? 'hidden md:inline-grid' : ''}`}
              style={{ background: currentNav ? softColour(currentNav.colour, '22') : 'var(--hs-primary-soft)' }}
            >
              {currentNav?.icon || '◇'}
            </span>
            <div className="min-w-0">
              <span className="block truncate text-sm font-extrabold tracking-tight text-ink sm:text-base">
                {currentNav?.label || 'HomeStack'}
              </span>
              <span className="hidden truncate text-[10px] font-medium text-muted sm:block">{currentNav?.description || 'Your household, together'}</span>
            </div>
          </div>
          <button
            onClick={() => setSearchOpen(true)}
            className="hidden h-11 min-w-11 place-items-center rounded-xl border border-transparent px-2 text-muted transition-colors hover:border-line hover:bg-sunken hover:text-ink md:flex md:gap-2 lg:min-w-[176px] lg:justify-start lg:border-line lg:bg-surface lg:px-3"
            aria-label="Search HomeStack"
            title={`Search (${SHORTCUT_MODIFIER}K)`}
          >
            <span className="text-lg">⌕</span><span className="hidden text-xs font-semibold lg:inline">Search anything</span><span className="ml-auto hidden rounded-md border border-line px-1.5 py-0.5 text-[9px] text-muted xl:inline">{SHORTCUT_MODIFIER}K</span>
          </button>
          <button
            onClick={() => setQuickOpen(true)}
            className="hidden h-11 min-w-11 place-items-center rounded-xl bg-primary px-2 text-white shadow-soft transition-all hover:bg-primary-hover active:scale-95 md:flex md:gap-1 md:px-3"
            aria-label="Create something"
            title="Create something"
          >
            <span className="text-lg leading-none">＋</span><span className="hidden text-xs font-semibold lg:inline">Create</span>
          </button>
          <div className="hidden lg:block"><CalendarPeek /></div>
          <NotificationBell />
          </div>
        </header>
        <ConnectionBanner />
        {contextualGuide && (
          <div className={`${CONTENT_CONTAINER} pt-2`}>
            <div className="flex items-center justify-end gap-1 text-[11px] text-muted">
              <NavLink to={`/settings/guides/${contextualGuide.key}`} className="rounded-lg px-2 py-1 font-semibold hover:bg-sunken hover:text-primary">
                ⓘ About {contextualGuide.label}
              </NavLink>
              <button type="button" onClick={() => hideContextualGuide(contextualGuide.key)} className="grid h-7 w-7 place-items-center rounded-lg hover:bg-sunken hover:text-ink" aria-label={`Hide the ${contextualGuide.label} guide link`} title="Hide this guide link">×</button>
            </div>
          </div>
        )}
        {stacksError && (
          <div className={`${CONTENT_CONTAINER} pt-4`}>
            <InlineAlert message={stacksError} onRetry={refreshStacks} />
          </div>
        )}
        <main className={`${CONTENT_CONTAINER} min-w-0 flex-1 py-5 pb-[calc(7.25rem+env(safe-area-inset-bottom))] md:py-7 md:pb-8`}>
          <Outlet />
        </main>
      </div>

      {/* Bottom nav — mobile only. Home, Add and More are fixed; the two remaining slots are
          user-configurable shortcuts either side of Add (docs/36 §4.2). */}
      <nav
        className="mobile-bottom-nav fixed bottom-[calc(0.625rem+env(safe-area-inset-bottom))] left-3 right-3 z-30 grid h-[72px] grid-cols-5 items-stretch rounded-[1.65rem] border border-line bg-surface/90 p-1.5 shadow-[0_12px_34px_rgba(25,32,36,0.22)] backdrop-blur-xl md:hidden"
        aria-label="Main navigation"
        data-floating-dock
      >
        {hubItem && <MobileNavLink item={hubItem} />}
        {mobileShortcuts[0] && <MobileNavLink item={mobileShortcuts[0]} />}
        <button
          onClick={() => setQuickOpen(true)}
          className="relative -translate-y-1 flex min-h-11 min-w-0 flex-col items-center justify-center rounded-[1.15rem] text-[10px] font-extrabold text-primary transition-transform duration-150 active:scale-[0.96] motion-reduce:transform-none motion-reduce:transition-none"
          aria-label="Create something"
          data-nav-key="add"
        >
          <span className="grid h-12 w-12 place-items-center rounded-full bg-primary text-2xl leading-none text-white shadow-[0_8px_18px_rgba(29,122,145,0.32)]">＋</span>
          <span className="mt-0.5 leading-3">Add</span>
        </button>
        {mobileShortcuts[1] && <MobileNavLink item={mobileShortcuts[1]} />}
        <button
          onClick={() => setMoreOpen(true)}
          style={moreOpen
            ? { color: 'var(--hs-primary)', background: 'var(--hs-primary-soft)' }
            : currentIsInMore
              ? { color: currentNav?.colour ?? 'var(--hs-primary)', background: currentNav ? softColour(currentNav.colour, '14') : 'var(--hs-primary-soft)' }
              : undefined}
          className={`relative flex min-h-11 min-w-0 flex-col items-center justify-center rounded-[1.15rem] px-0.5 py-1 text-[10px] font-extrabold transition-[background-color,color,transform] duration-150 active:scale-[0.96] motion-reduce:transform-none motion-reduce:transition-none ${moreOpen ? 'text-primary' : currentIsInMore ? '' : 'text-muted'}`}
          aria-label="More navigation and profile options"
          aria-haspopup="dialog"
          aria-expanded={moreOpen}
          data-nav-key="more"
        >
          <span
            className={`relative grid h-7 min-w-10 place-items-center rounded-full px-2 text-[19px] leading-none ${moreOpen ? 'bg-primary-soft' : ''}`}
            style={currentIsInMore && currentNav && !moreOpen ? { background: softColour(currentNav.colour, '24') } : undefined}
          >
            ☰
            {currentIsInMore && currentNav && !moreOpen && <span className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full" style={{ backgroundColor: currentNav.colour }} aria-hidden />}
          </span>
          <span className="mt-0.5 max-w-full truncate px-0.5 leading-3">More</span>
        </button>
      </nav>

      {moreOpen && (
        <MoreSheet
          user={user}
          editingProfile={editingProfile}
          setEditingProfile={setEditingProfile}
          updateUser={updateUser}
          stackNav={stackNav}
          customisingNav={customisingNav}
          setCustomisingNav={setCustomisingNav}
          effectiveMobileKeys={effectiveMobileKeys}
          setMobileSlot={setMobileSlot}
          resetMobileKeys={resetMobileKeys}
          adminNav={adminNav}
          dark={dark}
          setDark={setDark}
          onSearch={() => setSearchOpen(true)}
          logout={logout}
          onClose={() => setMoreOpen(false)}
        />
      )}
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} enabledKeys={enabledKeys} />
      <QuickCreate open={quickOpen} onClose={() => setQuickOpen(false)} enabledKeys={enabledKeys} contextKey={currentNav?.key} />
      <DialogHost />
    </div>
  )
}
