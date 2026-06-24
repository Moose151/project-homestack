import { useEffect, useState } from 'react'

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
      className="flex flex-col items-center justify-center w-full h-full bg-gray-950 text-white cursor-pointer select-none"
      onClick={onStart}
    >
      <p className="text-9xl font-thin tracking-widest tabular-nums">{timeStr}</p>
      <p className="mt-4 text-2xl font-light text-gray-400">{dateStr}</p>
      <p className="mt-16 text-lg text-gray-600 animate-pulse">Tap anywhere to start</p>
    </div>
  )
}
