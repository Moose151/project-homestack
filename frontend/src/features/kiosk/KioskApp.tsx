/**
 * KioskApp — state machine for the kiosk mode.
 *
 * States
 * ------
 *   ambient       → tap anywhere → avatar_select
 *   avatar_select → select user  → pin_entry
 *   pin_entry     → correct PIN  → dashboard
 *               → back          → avatar_select
 *   dashboard     → 5 min idle  → avatar_select (via useInactivityTimeout)
 *               → sign out     → avatar_select
 */
import { useState } from 'react'
import type { AuthUser, KioskUser } from '../../api/types'
import { AmbientScreen } from './screens/AmbientScreen'
import { AvatarSelect } from './screens/AvatarSelect'
import { KioskDashboard } from './screens/KioskDashboard'
import { PINEntry } from './screens/PINEntry'

type KioskState = 'ambient' | 'avatar_select' | 'pin_entry' | 'dashboard'

export function KioskApp() {
  const [state, setState] = useState<KioskState>('ambient')
  const [selectedUser, setSelectedUser] = useState<KioskUser | null>(null)
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)

  const goToAvatarSelect = () => {
    setSelectedUser(null)
    setAuthUser(null)
    setState('avatar_select')
  }

  const handleUserSelect = (user: KioskUser) => {
    setSelectedUser(user)
    setState('pin_entry')
  }

  const handlePINSuccess = (user: AuthUser) => {
    setAuthUser(user)
    setState('dashboard')
  }

  return (
    <div className="w-screen h-screen overflow-hidden">
      {state === 'ambient' && (
        <AmbientScreen onStart={() => setState('avatar_select')} />
      )}
      {state === 'avatar_select' && (
        <AvatarSelect onSelect={handleUserSelect} />
      )}
      {state === 'pin_entry' && selectedUser && (
        <PINEntry
          kioskUser={selectedUser}
          onSuccess={handlePINSuccess}
          onCancel={goToAvatarSelect}
        />
      )}
      {state === 'dashboard' && authUser && (
        <KioskDashboard authUser={authUser} onLogout={goToAvatarSelect} />
      )}
    </div>
  )
}
