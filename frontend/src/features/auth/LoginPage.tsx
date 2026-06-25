import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { useAuth } from './AuthContext'
import { PINPad } from '../../components/PINPad'
import { Avatar } from '../../components/Avatar'
import type { KioskUser } from '../../api/types'

type Step = 'select' | 'pin' | 'username'

export function LoginPage() {
  const { login } = useAuth()
  const [step, setStep] = useState<Step>('select')
  const [users, setUsers] = useState<KioskUser[]>([])
  const [selected, setSelected] = useState<KioskUser | null>(null)
  const [username, setUsername] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getKioskUsers()
      .then(setUsers)
      .catch(() => setError('Could not load household members.'))
  }, [])

  const pickUser = (u: KioskUser) => {
    setSelected(u)
    setUsername(u.username)
    setError(null)
    setStep('pin')
  }

  const startManual = (e: React.FormEvent) => {
    e.preventDefault()
    if (username.trim()) {
      setSelected(null)
      setError(null)
      setStep('pin')
    }
  }

  const handlePIN = async (pin: string) => {
    setLoading(true)
    setError(null)
    try {
      const user = await api.pinLogin(username.trim(), pin)
      login(user)
    } catch {
      setError('Incorrect PIN. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">HomeStack</h1>
          <p className="text-muted mt-1">Welcome back</p>
        </div>

        <div className="bg-surface rounded-2xl shadow-card border border-line p-8">
          {step === 'select' ? (
            <div className="flex flex-col gap-5">
              <p className="text-center text-muted-strong font-medium">Who's signing in?</p>
              {error && <p className="text-danger text-sm text-center">{error}</p>}
              <div className="grid grid-cols-3 gap-3">
                {users.map(u => (
                  <button
                    key={u.person_id}
                    onClick={() => pickUser(u)}
                    className="flex flex-col items-center gap-2 p-3 rounded-2xl hover:bg-sunken active:scale-95 transition-all"
                  >
                    <Avatar name={u.display_name} colour={u.colour} avatar={u.avatar} size="lg" />
                    <span className="text-xs font-semibold text-ink truncate max-w-full">{u.preferred_name}</span>
                  </button>
                ))}
                {users.length === 0 && !error && (
                  <p className="col-span-3 text-center text-muted text-sm py-4">Loading…</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => { setUsername(''); setStep('username') }}
                className="text-xs text-muted hover:text-ink transition-colors text-center mt-1"
              >
                Sign in with a username instead
              </button>
            </div>
          ) : step === 'username' ? (
            <form onSubmit={startManual} className="flex flex-col gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-muted-strong">Username</span>
                <input
                  autoFocus
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="px-4 py-3 rounded-xl border border-line bg-raised text-ink focus:outline-none focus:ring-2 focus:ring-primary text-base"
                  placeholder="Enter your username"
                  autoCapitalize="none"
                  autoCorrect="off"
                />
              </label>
              <button
                type="submit"
                disabled={!username.trim()}
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary-hover text-white font-semibold transition-colors disabled:opacity-40 min-h-[48px] shadow-soft"
              >
                Continue
              </button>
              <button
                type="button"
                onClick={() => { setError(null); setStep('select') }}
                className="text-sm text-muted hover:text-ink transition-colors"
              >
                ← Back to members
              </button>
            </form>
          ) : (
            <div className="flex flex-col items-center gap-4">
              {selected
                ? (
                  <div className="flex flex-col items-center gap-2">
                    <Avatar name={selected.display_name} colour={selected.colour} avatar={selected.avatar} size="lg" />
                    <p className="text-muted-strong font-medium">{selected.preferred_name}</p>
                  </div>
                )
                : (
                  <p className="text-muted-strong font-medium">
                    PIN for <span className="text-primary font-semibold">{username}</span>
                  </p>
                )}
              <PINPad
                length={4}
                onComplete={handlePIN}
                loading={loading}
                error={error}
                onClear={() => setError(null)}
              />
              <button
                type="button"
                onClick={() => { setStep('select'); setSelected(null); setError(null) }}
                className="text-sm text-muted hover:text-ink transition-colors mt-2"
              >
                ← Back
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
