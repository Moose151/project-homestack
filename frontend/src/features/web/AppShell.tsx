import { NavLink, Outlet } from 'react-router-dom'
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

interface NavItem { label: string; route: string; icon: string; colour: string }

// How many stacks (in STACKS order) get a dedicated slot in the mobile bottom bar
// before the rest collapse into the "More" sheet. Keeps the bar to 5 tap targets.
const MOBILE_PRIMARY_SLOTS = 4

const EMOJI_OPTS = ['🐱','🐶','🦊','🐼','🐻','🦋','🦄','🐸','🐳','🌻','🌙','⭐','🎸','🎮','🏄','🍕','🎩','🔮','🌈','🦅']

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

/** A single sidebar link. Accent-coloured when active; muted otherwise. */
function SidebarLink({ item, accent }: { item: NavItem; accent: boolean }) {
  const activeStyle = ({ isActive }: { isActive: boolean }): CSSProperties | undefined =>
    isActive && accent ? { background: softColour(item.colour, '22'), color: item.colour } : undefined
  return (
    <NavLink
      to={item.route}
      style={activeStyle}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
          isActive ? (accent ? '' : 'bg-sunken text-ink') : 'text-muted-strong hover:bg-sunken'
        }`
      }
    >
      <span className="text-lg w-6 text-center">{item.icon}</span>
      {item.label}
    </NavLink>
  )
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="px-3 pt-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-muted/70 select-none">
      {children}
    </p>
  )
}

export function AppShell() {
  const { user, logout, updateUser } = useAuth()
  const [dark, setDark] = useDarkMode()
  const [editingProfile, setEditingProfile] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const { enabledKeys } = useStacks()

  // Core surfaces (Hub, Calendar) always show; node-backed stacks only when enabled.
  const coreNav: NavItem[] = STACKS
    .filter(s => !s.isNode)
    .map(s => ({ label: s.label, route: s.route, icon: s.icon, colour: s.colour }))
  const nodeNav: NavItem[] = STACKS
    .filter(s => s.isNode && enabledKeys.has(s.key))
    .map(s => ({ label: s.label, route: s.route, icon: s.icon, colour: s.colour }))
  const stackNav: NavItem[] = [...coreNav, ...nodeNav]

  const adminNav: NavItem[] = user?.role === 'admin'
    ? [
        { label: 'Users', route: '/users', icon: '👥', colour: 'var(--hs-muted-strong)' },
        { label: 'Settings', route: '/settings', icon: '⚙️', colour: 'var(--hs-muted-strong)' },
      ]
    : []

  // Mobile bottom bar: a few primary stacks get their own slot; everything else
  // (remaining stacks + admin + utilities) lives behind the "More" sheet.
  const mobilePrimary = stackNav.slice(0, MOBILE_PRIMARY_SLOTS)
  const mobileOverflow = stackNav.slice(MOBILE_PRIMARY_SLOTS)

  // Close the More sheet on Escape.
  useEffect(() => {
    if (!moreOpen) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMoreOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [moreOpen])

  return (
    <div className="min-h-screen flex">
      {/* Sidebar — md+ */}
      <aside className="hidden md:flex flex-col w-56 bg-surface/90 backdrop-blur border-r border-line fixed inset-y-0 left-0 z-20">
        <div className="px-5 h-16 border-b border-line flex items-center gap-2">
          <span className="inline-grid place-items-center w-9 h-9 rounded-xl bg-primary text-white shadow-soft">◇</span>
          <span className="text-xl font-extrabold tracking-tight text-ink">HomeStack</span>
        </div>

        <nav className="flex-1 px-3 py-3 flex flex-col gap-0.5 overflow-y-auto">
          <SectionLabel>Core</SectionLabel>
          {coreNav.map(item => <SidebarLink key={item.route} item={item} accent />)}

          {nodeNav.length > 0 && <SectionLabel>Nodes</SectionLabel>}
          {nodeNav.map(item => <SidebarLink key={item.route} item={item} accent />)}

          {adminNav.length > 0 && (
            <>
              <SectionLabel>Admin</SectionLabel>
              {adminNav.map(item => <SidebarLink key={item.route} item={item} accent={false} />)}
            </>
          )}
        </nav>

        <div className="px-4 py-4 border-t border-line flex flex-col gap-2">
          <button
            onClick={() => setDark(!dark)}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted hover:bg-sunken transition-colors"
          >
            {dark ? '☀ Light' : '☾ Dark'}
          </button>
          <a
            href="/kiosk"
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted hover:bg-sunken transition-colors"
          >
            <span className="text-lg">▣</span> Enter kiosk
          </a>
          {user && (
            <>
              <div className="flex items-center gap-2 px-1">
                <button onClick={() => setEditingProfile(v => !v)} className="flex-shrink-0" title="Edit profile">
                  <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="sm" />
                </button>
                <div className="flex-1 min-w-0">
                  <button onClick={() => setEditingProfile(v => !v)} className="text-left w-full">
                    <p className="text-sm font-semibold text-ink truncate hover:text-primary transition-colors">{user.display_name}</p>
                    <p className="text-xs text-muted capitalize">{user.role}</p>
                  </button>
                </div>
                <button
                  onClick={logout}
                  className="text-xs text-muted hover:text-danger transition-colors"
                  title="Sign out"
                >
                  ⊗
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
          <p className="text-center text-[10px] text-muted/50 select-none pt-1">v{APP_VERSION}</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 md:ml-56 flex flex-col min-h-screen">
        <header className="flex items-center gap-1 px-4 md:px-8 h-16 border-b border-line bg-surface/60 backdrop-blur sticky top-0 z-10">
          {/* Mobile brand — the sidebar (which holds the wordmark) is hidden on small screens. */}
          <div className="flex items-center gap-2 md:hidden mr-auto">
            <span className="inline-grid place-items-center w-8 h-8 rounded-lg bg-primary text-white shadow-soft text-sm">◇</span>
            <span className="text-lg font-extrabold tracking-tight text-ink">HomeStack</span>
          </div>
          <div className="hidden md:block mr-auto" />
          <CalendarPeek />
          <NotificationBell />
        </header>
        <main className="flex-1 w-full px-4 py-5 sm:px-5 md:px-8 lg:px-10 xl:px-12 md:py-8 max-w-[1600px] mx-auto pb-24 md:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Bottom nav — mobile only */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-surface/95 backdrop-blur border-t border-line flex z-30">
        {mobilePrimary.map(item => (
          <NavLink
            key={item.route}
            to={item.route}
            style={({ isActive }) => (isActive ? { color: item.colour } : undefined)}
            className={({ isActive }) =>
              `flex-1 min-w-0 flex flex-col items-center justify-center py-2.5 text-[11px] font-semibold transition-colors ${
                isActive ? '' : 'text-muted'
              }`
            }
          >
            <span className="text-xl mb-0.5">{item.icon}</span>
            <span className="truncate max-w-full px-1">{item.label}</span>
          </NavLink>
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className={`flex-1 min-w-0 flex flex-col items-center justify-center py-2.5 text-[11px] font-semibold transition-colors ${
            moreOpen ? 'text-primary' : 'text-muted'
          }`}
        >
          <span className="text-xl mb-0.5">☰</span>
          More
        </button>
      </nav>

      {/* Mobile "More" sheet — everything that didn't fit the bottom bar. */}
      {moreOpen && (
        <div className="md:hidden fixed inset-0 z-40" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setMoreOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 bg-surface rounded-t-3xl border-t border-line shadow-soft max-h-[85vh] overflow-y-auto pb-[env(safe-area-inset-bottom)]">
            <div className="sticky top-0 bg-surface/95 backdrop-blur flex items-center justify-between px-5 pt-4 pb-3 border-b border-line">
              <span className="text-base font-bold text-ink">All stacks</span>
              <button onClick={() => setMoreOpen(false)} className="w-8 h-8 grid place-items-center rounded-lg text-muted hover:bg-sunken" aria-label="Close">✕</button>
            </div>

            <div className="p-4 space-y-5">
              {mobileOverflow.length > 0 && (
                <div className="grid grid-cols-4 gap-2">
                  {mobileOverflow.map(item => (
                    <NavLink
                      key={item.route}
                      to={item.route}
                      onClick={() => setMoreOpen(false)}
                      style={({ isActive }) => (isActive ? { background: softColour(item.colour, '22'), color: item.colour } : undefined)}
                      className={({ isActive }) =>
                        `flex flex-col items-center gap-1.5 py-3 px-1 rounded-2xl text-[11px] font-semibold text-center transition-colors ${
                          isActive ? '' : 'text-muted-strong hover:bg-sunken'
                        }`
                      }
                    >
                      <span className="text-2xl">{item.icon}</span>
                      <span className="truncate max-w-full">{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}

              {adminNav.length > 0 && (
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted/70 mb-1.5 px-1">Admin</p>
                  <div className="flex flex-col gap-1">
                    {adminNav.map(item => (
                      <NavLink
                        key={item.route}
                        to={item.route}
                        onClick={() => setMoreOpen(false)}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                            isActive ? 'bg-sunken text-ink' : 'text-muted-strong hover:bg-sunken'
                          }`
                        }
                      >
                        <span className="text-lg w-6 text-center">{item.icon}</span>
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted/70 mb-1.5 px-1">More</p>
                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => { setDark(!dark); }}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-muted-strong hover:bg-sunken transition-colors text-left"
                  >
                    <span className="text-lg w-6 text-center">{dark ? '☀' : '☾'}</span>
                    {dark ? 'Light mode' : 'Dark mode'}
                  </button>
                  <a
                    href="/kiosk"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-muted-strong hover:bg-sunken transition-colors"
                  >
                    <span className="text-lg w-6 text-center">▣</span>
                    Enter kiosk
                  </a>
                  {user && (
                    <button
                      onClick={() => { setMoreOpen(false); logout() }}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-muted-strong hover:bg-sunken hover:text-danger transition-colors text-left"
                    >
                      <span className="text-lg w-6 text-center">⊗</span>
                      Sign out
                    </button>
                  )}
                </div>
              </div>

              {user && (
                <div className="flex items-center gap-3 px-1 pt-2 border-t border-line">
                  <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-ink truncate">{user.display_name}</p>
                    <p className="text-xs text-muted capitalize">{user.role}</p>
                  </div>
                  <span className="text-[10px] text-muted/50">v{APP_VERSION}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
