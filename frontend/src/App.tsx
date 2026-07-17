import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './features/auth/AuthContext'
import { LoginPage } from './features/auth/LoginPage'
import { AppShell } from './features/web/AppShell'
import { HubPage } from './features/web/pages/HubPage'
import { AtlasPage } from './features/web/pages/AtlasPage'
import { MeridianPage } from './features/web/pages/MeridianPage'
import { CalendarPage } from './features/web/pages/CalendarPage'
import { EducationPage } from './features/web/pages/EducationPage'
import { BooksPage } from './features/web/pages/BooksPage'
import { UsersPage } from './features/web/pages/UsersPage'
import { SettingsPage } from './features/web/pages/SettingsPage'
import { KioskApp } from './features/kiosk/KioskApp'
import { StacksProvider, useStacks } from './features/stacks/StacksContext'

// Node-backed stacks are only routable when the household has them enabled.
function NodeRoute({ nodeKey, children }: { nodeKey: string; children: React.ReactNode }) {
  const { enabledKeys, loading } = useStacks()
  if (loading) return null
  return enabledKeys.has(nodeKey) ? <>{children}</> : <Navigate to="/hub" replace />
}

function WebRoutes({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/hub" replace />} />
        <Route path="/hub" element={<HubPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/atlas" element={<NodeRoute nodeKey="atlas"><AtlasPage /></NodeRoute>} />
        <Route path="/meridian" element={<NodeRoute nodeKey="meridian"><MeridianPage /></NodeRoute>} />
        <Route path="/education" element={<NodeRoute nodeKey="education"><EducationPage /></NodeRoute>} />
        <Route path="/books" element={<NodeRoute nodeKey="books"><BooksPage /></NodeRoute>} />
        {isAdmin && <Route path="/users" element={<UsersPage />} />}
        {isAdmin && <Route path="/settings" element={<SettingsPage />} />}
        <Route path="*" element={<Navigate to="/hub" replace />} />
      </Route>
    </Routes>
  )
}

function WebApp() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) return <LoginPage />

  return (
    <StacksProvider>
      <WebRoutes isAdmin={user.role === 'admin'} />
    </StacksProvider>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/kiosk/*" element={<KioskApp />} />
      <Route
        path="/*"
        element={
          <AuthProvider>
            <WebApp />
          </AuthProvider>
        }
      />
    </Routes>
  )
}
