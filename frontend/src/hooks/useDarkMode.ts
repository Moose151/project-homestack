import { useEffect, useState } from 'react'

export function useDarkMode(): [boolean, (v: boolean) => void] {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('hs-dark')
    if (stored !== null) return stored === 'true'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('hs-dark', String(dark))
  }, [dark])

  return [dark, setDark]
}
