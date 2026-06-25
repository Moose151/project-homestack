import { useEffect, useState } from 'react'
import { KioskThemeToggle } from '../components/KioskThemeToggle'

interface Props {
  onStart: () => void
}

export function AmbientScreen({ onStart }: Props) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const pad = (n: number) => String(n).padStart(2, '0')
  const timeStr = `${pad(time.getHours())}:${pad(time.getMinutes())}`
  const dateStr = time.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  return (
    <div
      className="relative flex h-full w-full cursor-pointer select-none flex-col items-center justify-center bg-paper text-ink"
      onClick={onStart}
    >
      <div className="absolute right-6 top-5 flex items-center gap-3">
        <KioskThemeToggle />
        <a
          href="/"
          onClick={(e) => e.stopPropagation()}
          className="min-h-11 rounded-lg border border-line bg-surface/70 px-4 py-2 text-sm font-semibold text-muted shadow-soft transition-colors hover:bg-primary-soft hover:text-ink"
          title="Exit kiosk mode"
        >
          Exit kiosk
        </a>
      </div>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(201,138,61,0.14),transparent_24rem)]" />
      <div className="relative z-10 text-center">
        <p className="text-8xl font-thin tabular-nums text-ink sm:text-9xl">{timeStr}</p>
        <p className="mt-4 text-2xl font-light text-muted-strong">{dateStr}</p>
        <p className="mt-16 text-lg font-medium text-muted animate-pulse">Tap anywhere to start</p>
      </div>
    </div>
  )
}
