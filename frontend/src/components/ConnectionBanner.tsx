import { useEffect, useState } from 'react'

export function ConnectionBanner() {
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    const connected = () => setOnline(true)
    const disconnected = () => setOnline(false)
    window.addEventListener('online', connected)
    window.addEventListener('offline', disconnected)
    return () => {
      window.removeEventListener('online', connected)
      window.removeEventListener('offline', disconnected)
    }
  }, [])

  if (online) return null
  return (
    <div className="sticky top-16 z-20 bg-warning px-4 py-2 text-center text-xs font-semibold text-white">
      You’re offline. Changes will be available again when the connection returns.
    </div>
  )
}
