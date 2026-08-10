import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { NotificationBell } from '../../components/NotificationBell'
import { CalendarPeek } from '../../components/CalendarPeek'
import { useDarkMode } from '../../hooks/useDarkMode'
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

const NAV_GROUPS: Array<{ key: NavItem['group']; label: string }> = [
  { key: 'start', label: 'Start here' },
  { key: 'organise', label: 'Plan & organise' },
  { key: 'household', label: 'Household' },
  { key: 'money', label: 'Money' },
]

// How many stacks (in STACKS order) get a dedicated slot in the mobile bottom bar
// before the rest collapse into the "More" sheet. Keeps the bar to 5 tap targets.
const MOBILE_PRIMARY_SLOTS = 4
const MOBILE_DEFAULT_PRIORITY = [
  'hub', 'calendar', 'atlas', 'homestead', 'pets', 'home_wiki',
  'education', 'books', 'meridian', 'solace',
  'fitness',
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
      <div className="flex items-center gap-2">
        <input type="color" value={colour} onChange={e => setColour(e.target.value)}
          className="w-9 h-9 rounded-lg border border-line cursor-pointer p-0.5" title="Accent colour" />
        <span className="text-xs text-muted-strong flex-1">Accent colour</span>
        <Avatar name={name || '?'} colour={colour} avatar={avatar} size="md" />
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

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="px-3 pb-1 pt-3 text-[10px] font-extrabold uppercase tracking-[0.15em] text-muted/60 select-none">
      {children}
    </p>
  )
}

export function AppShell() {
  const { user, logout, updateUser } = useAuth()
  const location = useLocation()
  const [dark, setDark] = useDarkMode()
  const [editingProfile, setEditingProfile] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [customisingNav, setCustomisingNav] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const [mobileKeys, setMobileKeys] = useState<string[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('hs-mobile-nav') || '[]')
      return Array.isArray(saved) ? saved.filter((key): key is string => typeof key === 'string') : []
    } catch {
      return []
    }
  })
  const { enabledKeys, error: stacksError, refresh: refreshStacks } = useStacks()
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

  // Mobile bottom bar: a few primary stacks get their own slot; everything else
  // (remaining stacks + admin + utilities) lives behind the "More" sheet.
  const availableKeys = new Set(stackNav.map(item => item.key))
  const defaultMobileKeys = MOBILE_DEFAULT_PRIORITY
    .filter(key => availableKeys.has(key))
    .slice(0, MOBILE_PRIMARY_SLOTS)
  const effectiveMobileKeys = mobileKeys.length
    ? mobileKeys.filter(key => availableKeys.has(key)).slice(0, MOBILE_PRIMARY_SLOTS)
    : defaultMobileKeys
  const mobilePrimary = effectiveMobileKeys
    .map(key => stackNav.find(item => item.key === key))
    .filter((item): item is NavItem => Boolean(item))
  const currentNav = [...stackNav, ...adminNav].find(item => location.pathname.startsWith(item.route))
  // The destination the More button represents while you are on it, because it has no slot.
  const moreStandsIn = currentNav && !mobilePrimary.some(item => item.key === currentNav.key)
    ? currentNav
    : null

  const toggleMobileKey = (key: string) => {
    setMobileKeys(previous => {
      const current = previous.filter(item => availableKeys.has(item))
      const effective = current.length ? current : effectiveMobileKeys
      const next = effective.includes(key)
        ? effective.filter(item => item !== key)
        : effective.length < MOBILE_PRIMARY_SLOTS ? [...effective, key] : effective
      localStorage.setItem('hs-mobile-nav', JSON.stringify(next))
      return next
    })
  }

  // Close the More sheet on Escape.
  useEffect(() => {
    if (!moreOpen) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMoreOpen(false) }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKey)
    }
  }, [moreOpen])

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname, location.search])

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
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
          <span className="inline-grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-primary text-base font-black text-white shadow-soft">◇</span>
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
      <div className="flex min-h-screen flex-1 flex-col md:ml-[272px]">
        <header className="sticky top-0 z-10 h-[62px] border-b border-line bg-surface/82 backdrop-blur-xl md:h-[68px]">
          <div className={`${CONTENT_CONTAINER} flex h-full items-center gap-1.5`}>
          <div className="mr-auto flex min-w-0 items-center gap-2.5">
            <span
              className="inline-grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl text-lg shadow-sm"
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
            className="grid h-10 min-w-10 place-items-center rounded-xl border border-transparent px-2 text-muted transition-colors hover:border-line hover:bg-sunken hover:text-ink md:flex md:gap-2 lg:min-w-[176px] lg:justify-start lg:border-line lg:bg-surface lg:px-3"
            aria-label="Search HomeStack"
            title={`Search (${SHORTCUT_MODIFIER}K)`}
          >
            <span className="text-lg">⌕</span><span className="hidden text-xs font-semibold lg:inline">Search anything</span><span className="ml-auto hidden rounded-md border border-line px-1.5 py-0.5 text-[9px] text-muted xl:inline">{SHORTCUT_MODIFIER}K</span>
          </button>
          <button
            onClick={() => setQuickOpen(true)}
            className="grid h-10 min-w-10 place-items-center rounded-xl bg-primary px-2 text-white shadow-soft transition-all hover:bg-primary-hover active:scale-95 md:flex md:gap-1 md:px-3"
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
        {stacksError && (
          <div className={`${CONTENT_CONTAINER} pt-4`}>
            <InlineAlert message={stacksError} onRetry={refreshStacks} />
          </div>
        )}
        <main className={`${CONTENT_CONTAINER} flex-1 py-5 pb-[calc(6rem+env(safe-area-inset-bottom))] md:py-7 md:pb-8`}>
          <Outlet />
        </main>
      </div>

      {/* Bottom nav — mobile only */}
      <nav className="mobile-bottom-nav fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-surface/94 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_rgba(50,40,25,0.06)] backdrop-blur-xl md:hidden" aria-label="Main navigation">
        {mobilePrimary.map(item => (
          <NavLink
            key={item.route}
            to={item.route}
            style={({ isActive }) => (isActive ? { color: item.colour } : undefined)}
            className={({ isActive }) =>
              `relative flex min-w-0 flex-1 flex-col items-center justify-center pb-1.5 pt-1.5 text-[11px] font-bold transition-colors ${
                isActive ? '' : 'text-muted'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className="mb-0.5 grid h-8 min-w-11 place-items-center rounded-full px-2 text-xl transition-all" style={{ background: isActive ? softColour(item.colour, '24') : 'transparent' }}>{item.icon}</span>
                <span className="max-w-full truncate px-1">{item.shortLabel}</span>
                {isActive && <span className="absolute bottom-0 h-0.5 w-5 rounded-full" style={{ backgroundColor: item.colour }} />}
              </>
            )}
          </NavLink>
        ))}
        {/* When you are somewhere that has no slot of its own — Fitness, Books, Money — nothing
            in the bar used to be marked, so the phone gave no answer to "where am I". The More
            button then stands in for the current destination and wears its icon and colour. */}
        <button
          onClick={() => setMoreOpen(true)}
          style={moreStandsIn && !moreOpen ? { color: moreStandsIn.colour } : undefined}
          className={`relative flex min-w-0 flex-1 flex-col items-center justify-center pb-1.5 pt-1.5 text-[11px] font-bold transition-colors ${
            moreOpen || moreStandsIn ? '' : 'text-muted'
          } ${moreOpen ? 'text-primary' : ''}`}
          aria-label={moreStandsIn ? `${moreStandsIn.label} — open all destinations` : 'More navigation and profile options'}
        >
          <span
            className={`mb-0.5 grid h-8 min-w-11 place-items-center rounded-full px-2 text-xl ${moreOpen ? 'bg-primary-soft' : ''}`}
            style={moreStandsIn && !moreOpen ? { background: softColour(moreStandsIn.colour, '24') } : undefined}
          >
            {moreStandsIn && !moreOpen ? moreStandsIn.icon : '☰'}
          </span>
          <span className="max-w-full truncate px-1">{moreStandsIn && !moreOpen ? moreStandsIn.shortLabel : 'More'}</span>
          {(moreOpen || moreStandsIn) && (
            <span
              className="absolute bottom-0 h-0.5 w-5 rounded-full"
              style={{ backgroundColor: moreOpen || !moreStandsIn ? 'var(--hs-primary)' : moreStandsIn.colour }}
            />
          )}
        </button>
      </nav>

      {/* Mobile destination directory + profile/preferences. */}
      {moreOpen && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="HomeStack navigation">
          <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" onClick={() => setMoreOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 max-h-[90vh] overflow-y-auto rounded-t-[2rem] border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] shadow-card">
            <div className="sticky top-0 z-10 border-b border-line bg-surface/95 px-5 pb-3 pt-2 backdrop-blur-xl">
              <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line-strong" />
              <div className="flex items-center justify-between">
                <span>
                  <span className="block text-base font-extrabold text-ink">Go anywhere</span>
                  <span className="block text-xs text-muted">All your household spaces in one place</span>
                </span>
                <button onClick={() => setMoreOpen(false)} className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-sunken" aria-label="Close">✕</button>
              </div>
            </div>

            <div className="space-y-5 p-4">
              {user && (
                <div className="rounded-3xl border border-line p-3.5" style={{ background: `linear-gradient(135deg, ${softColour(user.colour || '#1d7a91', '18')}, var(--hs-surface) 68%)` }}>
                  <div className="flex items-center gap-3">
                    <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="md" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-extrabold text-ink">{user.display_name}</p>
                      <p className="text-xs font-semibold capitalize text-muted">{user.role} profile</p>
                    </div>
                    <button
                      onClick={() => setEditingProfile(value => !value)}
                      className="min-h-10 rounded-xl border border-line bg-surface/80 px-3 py-2 text-xs font-bold text-primary shadow-sm"
                    >
                      {editingProfile ? 'Done' : 'Edit'}
                    </button>
                  </div>
                  {editingProfile && (
                    <div className="mt-3">
                      <ProfileEditor
                        user={user}
                        onSaved={u => { updateUser(u); setEditingProfile(false) }}
                        onClose={() => setEditingProfile(false)}
                      />
                    </div>
                  )}
                </div>
              )}

              <div>
                <div className="mb-2 flex items-center justify-between gap-3 px-1">
                  <span>
                    <span className="block text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">Destinations</span>
                    {customisingNav && <span className="mt-0.5 block text-[11px] text-muted">Choose up to four for the bottom bar</span>}
                  </span>
                  <button onClick={() => setCustomisingNav(value => !value)} className="min-h-9 rounded-lg px-2 text-xs font-bold text-primary hover:bg-primary-soft">
                    {customisingNav ? 'Finish editing' : 'Edit bottom bar'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {stackNav.map(item => {
                    const pinned = effectiveMobileKeys.includes(item.key)
                    if (customisingNav) {
                      return (
                        <button
                          key={item.route}
                          onClick={() => toggleMobileKey(item.key)}
                          disabled={!pinned && effectiveMobileKeys.length >= MOBILE_PRIMARY_SLOTS}
                          className={`relative flex min-h-[72px] items-center gap-2.5 rounded-2xl border p-2.5 text-left transition-all ${
                            pinned ? 'border-primary/40 bg-primary-soft text-primary' : 'border-line bg-surface text-muted-strong disabled:opacity-40'
                          }`}
                        >
                          <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl text-xl" style={{ background: softColour(item.colour, '18') }}>{item.icon}</span>
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-extrabold">{item.label}</span>
                            <span className="mt-0.5 block text-[11px] font-medium opacity-70">{pinned ? 'In bottom bar' : 'Add to bottom bar'}</span>
                          </span>
                          <span className="absolute right-2 top-1.5 text-xs font-black">{pinned ? '✓' : '+'}</span>
                        </button>
                      )
                    }
                    return (
                      <NavLink
                        key={item.route}
                        to={item.route}
                        onClick={() => setMoreOpen(false)}
                        style={({ isActive }) => (isActive ? { borderColor: item.colour, background: softColour(item.colour, '14'), color: item.colour } : undefined)}
                        className={({ isActive }) => `flex min-h-[76px] items-center gap-2.5 rounded-2xl border p-2.5 text-left transition-all ${isActive ? 'shadow-sm' : 'border-line bg-surface text-muted-strong active:scale-[0.98]'}`}
                      >
                        <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl text-2xl" style={{ background: softColour(item.colour, '18') }}>{item.icon}</span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-extrabold">{item.label}</span>
                          <span className="mt-1 block text-[11px] leading-tight opacity-70">{item.description}</span>
                        </span>
                      </NavLink>
                    )
                  })}
                </div>
              </div>

              <div>
                <p className="mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">Quick actions</p>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => { setMoreOpen(false); setSearchOpen(true) }} className="flex min-h-12 items-center gap-2 rounded-2xl border border-line bg-surface px-3 text-sm font-bold text-ink"><span className="text-lg">⌕</span> Search</button>
                  <button onClick={() => { setMoreOpen(false); setQuickOpen(true) }} className="flex min-h-12 items-center gap-2 rounded-2xl bg-primary px-3 text-sm font-bold text-white shadow-soft"><span className="text-lg">＋</span> Add something</button>
                </div>
              </div>

              {adminNav.length > 0 && (
                <div>
                  <p className="mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">Manage</p>
                  <div className="grid grid-cols-2 gap-2">
                    {adminNav.map(item => (
                      <NavLink key={item.route} to={item.route} onClick={() => setMoreOpen(false)} className={({ isActive }) => `flex min-h-[64px] items-center gap-2.5 rounded-2xl border px-3 text-left ${isActive ? 'border-primary bg-primary-soft text-primary' : 'border-line bg-surface text-muted-strong'}`}>
                        <span className="text-xl">{item.icon}</span>
                        <span className="min-w-0"><span className="block truncate text-sm font-bold">{item.label}</span><span className="block truncate text-[11px] text-muted">{item.description}</span></span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.15em] text-muted/70">App & session</p>
                <div className="overflow-hidden rounded-2xl border border-line bg-surface">
                  <button
                    onClick={() => { setDark(!dark); }}
                    className="flex min-h-12 w-full items-center gap-3 border-b border-line px-3 text-left text-sm font-semibold text-muted-strong hover:bg-sunken"
                  >
                    <span className="text-lg w-6 text-center">{dark ? '☀' : '☾'}</span>
                    {dark ? 'Light mode' : 'Dark mode'}
                  </button>
                  <a
                    href="/kiosk"
                    className="flex min-h-12 items-center gap-3 border-b border-line px-3 text-sm font-semibold text-muted-strong hover:bg-sunken"
                  >
                    <span className="text-lg w-6 text-center">▣</span>
                    Enter kiosk
                  </a>
                  {user && (
                    <button
                      onClick={() => { setMoreOpen(false); logout() }}
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
      )}
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} enabledKeys={enabledKeys} />
      <QuickCreate open={quickOpen} onClose={() => setQuickOpen(false)} enabledKeys={enabledKeys} />
      <DialogHost />
    </div>
  )
}
