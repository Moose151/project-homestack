import { useState } from 'react'
import { api } from '../../api/client'
import { useAuth } from './AuthContext'
import { PINPad } from '../../components/PINPad'

type Step = 'username' | 'pin'

export function LoginPage() {
  const { login } = useAuth()
  const [step, setStep] = useState<Step>('username')
  const [username, setUsername] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleUsername = (e: React.FormEvent) => {
    e.preventDefault()
    if (username.trim()) {
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
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">HomeStack</h1>
          <p className="text-muted mt-1">Welcome back</p>
        </div>

        <div className="bg-surface rounded-2xl shadow-card border border-line p-8">
          {step === 'username' ? (
            <form onSubmit={handleUsername} className="flex flex-col gap-4">
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
            </form>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <p className="text-muted-strong font-medium">
                PIN for <span className="text-primary font-semibold">{username}</span>
              </p>
              <PINPad
                length={4}
                onComplete={handlePIN}
                loading={loading}
                error={error}
                onClear={() => setError(null)}
              />
              <button
                type="button"
                onClick={() => { setStep('username'); setError(null) }}
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
