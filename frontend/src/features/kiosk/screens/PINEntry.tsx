import { useEffect, useState } from 'react'
import type { KioskUser } from '../../../api/types'
import { api } from '../../../api/client'
import type { AuthUser } from '../../../api/types'

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
      className="w-20 h-20 rounded-full bg-gray-700 hover:bg-gray-600 active:bg-gray-500 active:scale-95 text-white text-3xl font-light transition-all select-none"
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
        i < digits.length ? 'bg-white border-white' : 'border-gray-500'
      }`}
    />
  ))

  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-gray-900 text-white gap-8">
      <div className="flex flex-col items-center gap-2">
        {kioskUser.avatar ? (
          <img src={kioskUser.avatar} alt="" className="w-16 h-16 rounded-full object-cover" />
        ) : (
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold"
            style={{ backgroundColor: kioskUser.colour || '#4B5563' }}
          >
            {kioskUser.preferred_name.slice(0, 2).toUpperCase()}
          </div>
        )}
        <p className="text-2xl font-light">{kioskUser.preferred_name}</p>
      </div>

      <div className="flex gap-4">{dots}</div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="grid grid-cols-3 gap-4">
        {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
          <PINButton key={d} label={d} onClick={() => push(d)} />
        ))}
        <button
          onClick={onCancel}
          className="w-20 h-20 rounded-full bg-transparent hover:bg-gray-800 text-gray-400 text-sm transition-all select-none"
        >
          Back
        </button>
        <PINButton label="0" onClick={() => push('0')} />
        <button
          onClick={pop}
          className="w-20 h-20 rounded-full bg-transparent hover:bg-gray-800 text-gray-400 text-2xl transition-all select-none"
          aria-label="Delete"
        >
          ⌫
        </button>
      </div>
    </div>
  )
}
