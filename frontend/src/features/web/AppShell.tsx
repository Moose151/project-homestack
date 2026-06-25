import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { NotificationBell } from '../../components/NotificationBell'
import { CalendarPeek } from '../../components/CalendarPeek'
import { useDarkMode } from '../../hooks/useDarkMode'

const NAV = [
  { to: '/hub',      label: 'Hub',      icon: '⊙' },
  { to: '/atlas',    label: 'Atlas',    icon: '☰' },
  { to: '/meridian', label: 'Meridian', icon: '★' },
  { to: '/calendar', label: 'Calendar', icon: '◫' },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const [dark, setDark] = useDarkMode()
  const nav = user?.role === 'admin'
    ? [...NAV, { to: '/users', label: 'Users', icon: '⚙' }]
    : NAV

  return (
    <div className="min-h-screen flex">
      {/* Sidebar — md+ */}
      <aside className="hidden md:flex flex-col w-56 bg-surface/90 backdrop-blur border-r border-line fixed inset-y-0 left-0 z-20">
        <div className="px-5 py-5 border-b border-line flex items-center gap-2">
          <span className="inline-grid place-items-center w-8 h-8 rounded-xl bg-primary-soft text-primary border border-line">◇</span>
          <span className="text-xl font-extrabold tracking-tight text-ink">HomeStack</span>
        </div>

        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {nav.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-primary-soft text-primary'
                    : 'text-muted-strong hover:bg-sunken'
                }`
              }
            >
              <span className="text-lg">{icon}</span>
              {label}
            </NavLink>
          ))}
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
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-surface/95 backdrop-blur border-t border-line flex z-20">
        {nav.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-3 text-xs font-semibold transition-colors ${
                isActive ? 'text-primary' : 'text-muted'
              }`
            }
          >
            <span className="text-xl mb-0.5">{icon}</span>
            {label}
          </NavLink>
        ))}
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
