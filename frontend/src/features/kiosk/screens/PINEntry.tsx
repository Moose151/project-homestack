import { useEffect, useState } from 'react'
import type { KioskUser } from '../../../api/types'
import { api } from '../../../api/client'
import type { AuthUser } from '../../../api/types'
import { isImageAvatar } from '../../../components/Avatar'
import { KioskThemeToggle } from '../components/KioskThemeToggle'

const PIN_LENGTH = 4

interface Props {
  kioskUser: KioskUser
  onSuccess: (authUser: AuthUser) => void
  onCancel: () => void
}

function PINButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="h-20 w-20 select-none rounded-2xl border-2 border-line bg-raised text-3xl font-bold text-ink shadow-soft transition-all hover:border-primary hover:bg-primary-soft active:scale-95"
    >
      {label}
    </button>
  )
}

export function PINEntry({ kioskUser, onSuccess, onCancel }: Props) {
  const [digits, setDigits] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const push = (d: string) => {
    if (loading) return
    setError(null)
    const next = [...digits, d]
    setDigits(next)
    if (next.length >= PIN_LENGTH) {
      submit(next.join(''))
    }
  }

  const pop = () => {
    setError(null)
    setDigits((prev) => prev.slice(0, -1))
  }

  // Allow typing the PIN on a hardware keyboard (in addition to the on-screen pad).
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key >= '0' && e.key <= '9') {
        e.preventDefault()
        push(e.key)
      } else if (e.key === 'Backspace') {
        e.preventDefault()
        pop()
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onCancel()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  })

  const submit = async (pin: string) => {
    setLoading(true)
    try {
      const user = await api.pinLogin(kioskUser.username, pin)
      onSuccess(user)
    } catch {
      setError('Incorrect PIN. Please try again.')
      setDigits([])
    } finally {
      setLoading(false)
    }
  }

  const dots = Array.from({ length: PIN_LENGTH }, (_, i) => (
    <div
      key={i}
      className={`w-5 h-5 rounded-full border-2 transition-all ${
        i < digits.length ? 'bg-primary border-primary' : 'border-line-strong'
      }`}
    />
  ))

  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center gap-8 bg-paper px-6 text-ink">
      <div className="absolute right-6 top-5">
        <KioskThemeToggle />
      </div>
      <div className="flex flex-col items-center gap-2">
        {kioskUser.avatar && isImageAvatar(kioskUser.avatar) ? (
          <img src={kioskUser.avatar} alt="" className="w-16 h-16 rounded-full object-cover" />
        ) : (
          <div
            className="flex h-20 w-20 items-center justify-center rounded-full text-4xl font-bold text-white shadow-soft"
            style={{ backgroundColor: kioskUser.colour || '#4B5563' }}
          >
            {kioskUser.avatar || kioskUser.preferred_name.slice(0, 2).toUpperCase()}
          </div>
        )}
        <p className="text-3xl font-extrabold">{kioskUser.preferred_name}</p>
        <p className="text-muted">Enter your 4-digit PIN</p>
      </div>

      <div className="flex gap-4">{dots}</div>

      {error && <p className="rounded-xl border border-danger bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">{error}</p>}

      <div className="grid grid-cols-3 gap-4">
        {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
          <PINButton key={d} label={d} onClick={() => push(d)} />
        ))}
        <button
          onClick={onCancel}
          className="h-20 w-20 select-none rounded-2xl text-sm font-semibold text-muted transition-all hover:bg-sunken"
        >
          Back
        </button>
        <PINButton label="0" onClick={() => push('0')} />
        <button
          onClick={pop}
          className="h-20 w-20 select-none rounded-2xl text-2xl text-muted transition-all hover:bg-sunken"
          aria-label="Delete"
        >
          ⌫
        </button>
      </div>
    </div>
  )
}
