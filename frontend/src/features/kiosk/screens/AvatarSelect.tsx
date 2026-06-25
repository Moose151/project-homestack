import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { KioskUser } from '../../../api/types'
import { isImageAvatar } from '../../../components/Avatar'
import { KioskThemeToggle } from '../components/KioskThemeToggle'

interface Props {
  onSelect: (user: KioskUser) => void
}

function AvatarCard({ user, onClick }: { user: KioskUser; onClick: () => void }) {
  const initials = user.preferred_name.slice(0, 2).toUpperCase()
  const bg = user.colour || '#4B5563'
  const isImage = !!user.avatar && isImageAvatar(user.avatar)

  return (
    <button
      onClick={onClick}
      className="flex min-h-[180px] min-w-[160px] cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-line bg-raised p-6 text-ink shadow-soft transition-all hover:-translate-y-0.5 hover:border-primary hover:shadow-card active:scale-95"
    >
      {isImage ? (
        <img src={user.avatar} alt={user.display_name} className="w-24 h-24 rounded-full object-cover" />
      ) : (
        <div
          className="flex h-24 w-24 items-center justify-center rounded-full text-5xl font-bold text-white shadow-soft"
          style={{ backgroundColor: bg }}
        >
          {user.avatar || initials}
        </div>
      )}
      <span className="text-xl font-bold">{user.preferred_name}</span>
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
    <div className="relative flex h-full w-full flex-col items-center justify-center gap-10 bg-paper px-8 text-ink">
      <div className="absolute right-6 top-5">
        <KioskThemeToggle />
      </div>
      <div className="text-center">
        <h1 className="text-4xl font-extrabold">Who's here?</h1>
        <p className="mt-2 text-lg text-muted">Tap your picture to get started.</p>
      </div>
      {error && <p className="rounded-xl border border-danger bg-danger-soft px-4 py-3 text-danger">{error}</p>}
      <div className="flex flex-wrap justify-center gap-6">
        {users.map((u) => (
          <AvatarCard key={u.person_id} user={u} onClick={() => onSelect(u)} />
        ))}
        {!error && users.length === 0 && (
          <p className="text-muted">Loading...</p>
        )}
      </div>
    </div>
  )
}
