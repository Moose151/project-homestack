import { useEffect, useState } from 'react'

// Relative path — proxied to the backend container by the Vite dev server (see vite.config.ts).
const BACKEND_HEALTH_URL = '/api/v1/health/'

type Health = { status: string; service: string; phase: string }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(BACKEND_HEALTH_URL)
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setError('backend unreachable'))
  }, [])

  return (
    <main
      style={{
        fontFamily: 'system-ui, sans-serif',
        maxWidth: 640,
        margin: '4rem auto',
        padding: '0 1.5rem',
        lineHeight: 1.5,
      }}
    >
      <h1>HomeStack</h1>
      <p>Phase 1.0 — walking-skeleton scaffold. The stack is up.</p>
      <p>
        Backend health:{' '}
        {health ? (
          <strong>{`${health.status} (${health.service}, phase ${health.phase})`}</strong>
        ) : (
          <em>{error ?? 'checking…'}</em>
        )}
      </p>
    </main>
  )
}
