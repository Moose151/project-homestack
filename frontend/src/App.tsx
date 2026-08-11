import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './features/auth/AuthContext'
import { LoginPage } from './features/auth/LoginPage'
import { AppShell } from './features/web/AppShell'
import { StacksProvider, useStacks } from './features/stacks/StacksContext'

const HubPage = lazy(() => import('./features/web/pages/HubPage').then(m => ({ default: m.HubPage })))
const AtlasPage = lazy(() => import('./features/web/pages/AtlasPage').then(m => ({ default: m.AtlasPage })))
const MeridianPage = lazy(() => import('./features/web/pages/MeridianPage').then(m => ({ default: m.MeridianPage })))
const CalendarPage = lazy(() => import('./features/web/pages/CalendarPage').then(m => ({ default: m.CalendarPage })))
const EducationPage = lazy(() => import('./features/web/pages/EducationPage').then(m => ({ default: m.EducationPage })))
const BooksPage = lazy(() => import('./features/web/pages/BooksPage').then(m => ({ default: m.BooksPage })))
const HomeWikiPage = lazy(() => import('./features/web/pages/HomeWikiPage').then(m => ({ default: m.HomeWikiPage })))
const PetsPage = lazy(() => import('./features/web/pages/PetsPage').then(m => ({ default: m.PetsPage })))
const HomesteadPage = lazy(() => import('./features/web/pages/HomesteadPage').then(m => ({ default: m.HomesteadPage })))
const HomesteadRoomPage = lazy(() => import('./features/web/pages/HomesteadRoomPage').then(m => ({ default: m.HomesteadRoomPage })))
const SolacePage = lazy(() => import('./features/web/pages/SolacePage').then(m => ({ default: m.SolacePage })))
const FitnessPage = lazy(() => import('./features/web/pages/FitnessPage').then(m => ({ default: m.FitnessPage })))
const TravelPage = lazy(() => import('./features/web/pages/TravelPage').then(m => ({ default: m.TravelPage })))
const CornerPage = lazy(() => import('./features/web/pages/CornerPage').then(m => ({ default: m.CornerPage })))
const UsersPage = lazy(() => import('./features/web/pages/UsersPage').then(m => ({ default: m.UsersPage })))
const SettingsPage = lazy(() => import('./features/web/pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const KioskApp = lazy(() => import('./features/kiosk/KioskApp').then(m => ({ default: m.KioskApp })))

function RouteFallback() {
  return (
    <div className="grid min-h-[14rem] place-items-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  )
}

function Deferred({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>
}

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
        <Route path="/hub" element={<Deferred><HubPage /></Deferred>} />
        <Route path="/calendar" element={<Deferred><CalendarPage /></Deferred>} />
        <Route path="/corners" element={<Deferred><CornerPage /></Deferred>} />
        <Route path="/corners/:personId" element={<Deferred><CornerPage /></Deferred>} />
        <Route path="/atlas" element={<NodeRoute nodeKey="atlas"><Deferred><AtlasPage /></Deferred></NodeRoute>} />
        <Route path="/meridian" element={<NodeRoute nodeKey="meridian"><Deferred><MeridianPage /></Deferred></NodeRoute>} />
        <Route path="/education" element={<NodeRoute nodeKey="education"><Deferred><EducationPage /></Deferred></NodeRoute>} />
        <Route path="/books" element={<NodeRoute nodeKey="books"><Deferred><BooksPage /></Deferred></NodeRoute>} />
        <Route path="/wiki" element={<NodeRoute nodeKey="home_wiki"><Deferred><HomeWikiPage /></Deferred></NodeRoute>} />
        <Route path="/pets" element={<NodeRoute nodeKey="pets"><Deferred><PetsPage /></Deferred></NodeRoute>} />
        <Route path="/homestead" element={<NodeRoute nodeKey="homestead"><Deferred><HomesteadPage /></Deferred></NodeRoute>} />
        <Route path="/homestead/rooms/:roomId" element={<NodeRoute nodeKey="homestead"><Deferred><HomesteadRoomPage /></Deferred></NodeRoute>} />
        <Route path="/solace" element={<NodeRoute nodeKey="solace"><Deferred><SolacePage /></Deferred></NodeRoute>} />
        <Route path="/fitness" element={<NodeRoute nodeKey="fitness"><Deferred><FitnessPage /></Deferred></NodeRoute>} />
        <Route path="/travel" element={<NodeRoute nodeKey="travel"><Deferred><TravelPage /></Deferred></NodeRoute>} />
        {isAdmin && <Route path="/users" element={<Deferred><UsersPage /></Deferred>} />}
        {isAdmin && <Route path="/settings" element={<Deferred><SettingsPage /></Deferred>} />}
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
      <Route path="/kiosk/*" element={<Deferred><KioskApp /></Deferred>} />
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
