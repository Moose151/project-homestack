import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './features/auth/AuthContext'
import { LoginPage } from './features/auth/LoginPage'
import { AppShell } from './features/web/AppShell'
import { HubPage } from './features/web/pages/HubPage'
import { AtlasPage } from './features/web/pages/AtlasPage'
import { MeridianPage } from './features/web/pages/MeridianPage'
import { CalendarPage } from './features/web/pages/CalendarPage'
import { UsersPage } from './features/web/pages/UsersPage'
import { KioskApp } from './features/kiosk/KioskApp'

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
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/hub" replace />} />
        <Route path="/hub" element={<HubPage />} />
        <Route path="/atlas" element={<AtlasPage />} />
        <Route path="/meridian" element={<MeridianPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        {user.role === 'admin' && <Route path="/users" element={<UsersPage />} />}
        <Route path="*" element={<Navigate to="/hub" replace />} />
      </Route>
    </Routes>
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
