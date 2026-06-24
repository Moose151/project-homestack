import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { KioskUser } from '../../../api/types'

interface Props {
  onSelect: (user: KioskUser) => void
}

function AvatarCard({ user, onClick }: { user: KioskUser; onClick: () => void }) {
  const initials = user.preferred_name.slice(0, 2).toUpperCase()
  const bg = user.colour || '#4B5563'

  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-4 p-6 rounded-2xl bg-gray-800 hover:bg-gray-700 active:scale-95 transition-all cursor-pointer border-2 border-transparent hover:border-white/20 min-w-[160px]"
    >
      {user.avatar ? (
        <img src={user.avatar} alt={user.display_name} className="w-24 h-24 rounded-full object-cover" />
      ) : (
        <div
          className="w-24 h-24 rounded-full flex items-center justify-center text-3xl font-bold text-white"
          style={{ backgroundColor: bg }}
        >
          {initials}
        </div>
      )}
      <span className="text-white text-xl font-medium">{user.preferred_name}</span>
    </button>
  )
}

export function AvatarSelect({ onSelect }: Props) {
  const [users, setUsers] = useState<KioskUser[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getKioskUsers()
      .then(setUsers)
      .catch(() => setError('Could not load household members.'))
  }, [])

  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-gray-900 text-white gap-12 px-8">
      <h1 className="text-4xl font-light text-gray-200">Who are you?</h1>
      {error && <p className="text-red-400">{error}</p>}
      <div className="flex flex-wrap justify-center gap-6">
        {users.map((u) => (
          <AvatarCard key={u.person_id} user={u} onClick={() => onSelect(u)} />
        ))}
        {!error && users.length === 0 && (
          <p className="text-gray-500">Loading…</p>
        )}
      </div>
    </div>
  )
}
