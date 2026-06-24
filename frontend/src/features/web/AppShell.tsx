import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { useDarkMode } from '../../hooks/useDarkMode'

const NAV = [
  { to: '/hub',      label: 'Hub',      icon: '⊙' },
  { to: '/atlas',    label: 'Atlas',    icon: '☰' },
  { to: '/calendar', label: 'Calendar', icon: '◫' },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const [dark, setDark] = useDarkMode()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex">
      {/* Sidebar — md+ */}
      <aside className="hidden md:flex flex-col w-56 bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 fixed inset-y-0 left-0 z-20">
        <div className="px-5 py-5 border-b border-gray-100 dark:border-gray-800">
          <span className="text-xl font-semibold text-gray-900 dark:text-white">HomeStack</span>
        </div>

        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`
              }
            >
              <span className="text-lg">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-gray-100 dark:border-gray-800 flex flex-col gap-2">
          <button
            onClick={() => setDark(!dark)}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            {dark ? '☀ Light' : '☾ Dark'}
          </button>
          {user && (
            <div className="flex items-center gap-2 px-1">
              <Avatar name={user.display_name} colour={user.colour} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{user.display_name}</p>
                <p className="text-xs text-gray-400 capitalize">{user.role}</p>
              </div>
              <button
                onClick={logout}
                className="text-xs text-gray-400 hover:text-red-500 transition-colors"
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
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8 max-w-4xl w-full mx-auto pb-24 md:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Bottom nav — mobile only */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 flex z-20 safe-area-pb">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-3 text-xs font-medium transition-colors ${
                isActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-500 dark:text-gray-500'
              }`
            }
          >
            <span className="text-xl mb-0.5">{icon}</span>
            {label}
          </NavLink>
        ))}
        <button
          onClick={() => setDark(!dark)}
          className="flex-none flex flex-col items-center justify-center px-4 py-3 text-xs text-gray-400"
        >
          <span className="text-xl mb-0.5">{dark ? '☀' : '☾'}</span>
        </button>
      </nav>
    </div>
  )
}
