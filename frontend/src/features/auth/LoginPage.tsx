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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-white">HomeStack</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Welcome back</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-8">
          {step === 'username' ? (
            <form onSubmit={handleUsername} className="flex flex-col gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Username</span>
                <input
                  autoFocus
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
                  placeholder="Enter your username"
                  autoCapitalize="none"
                  autoCorrect="off"
                />
              </label>
              <button
                type="submit"
                disabled={!username.trim()}
                className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-40 min-h-[48px]"
              >
                Continue
              </button>
            </form>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <p className="text-gray-700 dark:text-gray-300 font-medium">
                PIN for <span className="text-blue-600">{username}</span>
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
                className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors mt-2"
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
