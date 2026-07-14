import { NavLink, Outlet } from 'react-router-dom'
import type { CSSProperties } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { NotificationBell } from '../../components/NotificationBell'
import { CalendarPeek } from '../../components/CalendarPeek'
import { useDarkMode } from '../../hooks/useDarkMode'
import { useStacks } from '../stacks/StacksContext'
import { STACKS, softColour } from '../../config/stacks'

interface NavItem { label: string; route: string; icon: string; colour: string }

export function AppShell() {
  const { user, logout } = useAuth()
  const [dark, setDark] = useDarkMode()
  const { enabledKeys } = useStacks()

  // Core surfaces (Hub, Calendar) always show; node-backed stacks only when enabled.
  const stackNav: NavItem[] = STACKS
    .filter(s => !s.isNode || enabledKeys.has(s.key))
    .map(s => ({ label: s.label, route: s.route, icon: s.icon, colour: s.colour }))

  const adminNav: NavItem[] = user?.role === 'admin'
    ? [
        { label: 'Users', route: '/users', icon: '👥', colour: 'var(--hs-muted-strong)' },
        { label: 'Settings', route: '/settings', icon: '⚙️', colour: 'var(--hs-muted-strong)' },
      ]
    : []

  const activeStyle = (colour: string) => ({ isActive }: { isActive: boolean }): CSSProperties | undefined =>
    isActive ? { background: softColour(colour, '22'), color: colour } : undefined

  return (
    <div className="min-h-screen flex">
      {/* Sidebar — md+ */}
      <aside className="hidden md:flex flex-col w-56 bg-surface/90 backdrop-blur border-r border-line fixed inset-y-0 left-0 z-20">
        <div className="px-5 py-5 border-b border-line flex items-center gap-2">
          <span className="inline-grid place-items-center w-9 h-9 rounded-xl bg-primary text-white shadow-soft">◇</span>
          <span className="text-xl font-extrabold tracking-tight text-ink">HomeStack</span>
        </div>

        <nav className="flex-1 px-3 py-4 flex flex-col gap-1 overflow-y-auto">
          {stackNav.map(item => (
            <NavLink
              key={item.route}
              to={item.route}
              style={activeStyle(item.colour)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                  isActive ? '' : 'text-muted-strong hover:bg-sunken'
                }`
              }
            >
              <span className="text-lg w-6 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}

          {adminNav.length > 0 && (
            <div className="mt-2 pt-2 border-t border-line flex flex-col gap-1">
              {adminNav.map(item => (
                <NavLink
                  key={item.route}
                  to={item.route}
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
            <div className="flex items-center gap-2 px-1">
              <Avatar name={user.display_name} colour={user.colour} avatar={user.avatar} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-ink truncate">{user.display_name}</p>
                <p className="text-xs text-muted capitalize">{user.role}</p>
              </div>
              <button
                onClick={logout}
                className="text-xs text-muted hover:text-danger transition-colors"
                title="Sign out"
              >
                ⊗
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 md:ml-56 flex flex-col min-h-screen">
        <header className="flex items-center justify-end gap-1 px-4 md:px-8 py-3 border-b border-line bg-surface/60 backdrop-blur sticky top-0 z-10">
          <CalendarPeek />
          <NotificationBell />
        </header>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8 max-w-4xl w-full mx-auto pb-24 md:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Bottom nav — mobile only */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-surface/95 backdrop-blur border-t border-line flex z-20 overflow-x-auto">
        {stackNav.map(item => (
          <NavLink
            key={item.route}
            to={item.route}
            style={({ isActive }) => (isActive ? { color: item.colour } : undefined)}
            className={({ isActive }) =>
              `flex-1 min-w-[4rem] flex flex-col items-center justify-center py-3 text-xs font-semibold transition-colors ${
                isActive ? '' : 'text-muted'
              }`
            }
          >
            <span className="text-xl mb-0.5">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
        {user?.role === 'admin' && (
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex-none flex flex-col items-center justify-center px-4 py-3 text-xs ${isActive ? 'text-ink' : 'text-muted'}`
            }
          >
            <span className="text-xl mb-0.5">⚙️</span>
          </NavLink>
        )}
        <button
          onClick={() => setDark(!dark)}
          className="flex-none flex flex-col items-center justify-center px-4 py-3 text-xs text-muted"
        >
          <span className="text-xl mb-0.5">{dark ? '☀' : '☾'}</span>
        </button>
      </nav>
    </div>
  )
}
