import { useState } from 'react'

interface Props {
  length?: number
  onComplete: (pin: string) => void
  loading?: boolean
  error?: string | null
  onClear?: () => void
}

function PadButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-16 h-16 rounded-full bg-sunken hover:bg-line active:scale-95 text-ink text-2xl font-light transition-all select-none"
    >
      {label}
    </button>
  )
}

export function PINPad({ length = 4, onComplete, loading = false, error, onClear }: Props) {
  const [digits, setDigits] = useState<string[]>([])

  const push = (d: string) => {
    if (loading) return
    const next = [...digits, d]
    setDigits(next)
    if (next.length >= length) {
      onComplete(next.join(''))
      setDigits([])
    }
  }

  const pop = () => {
    setDigits(prev => prev.slice(0, -1))
    onClear?.()
  }

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="flex gap-3">
        {Array.from({ length }, (_, i) => (
          <div
            key={i}
            className={`w-4 h-4 rounded-full border-2 transition-all ${
              i < digits.length ? 'bg-primary border-primary' : 'border-line-strong'
            }`}
          />
        ))}
      </div>

      {error && <p className="text-danger text-sm text-center">{error}</p>}

      <div className="grid grid-cols-3 gap-3">
        {['1','2','3','4','5','6','7','8','9'].map(d => (
          <PadButton key={d} label={d} onClick={() => push(d)} />
        ))}
        <div />
        <PadButton label="0" onClick={() => push('0')} />
        <button
          type="button"
          onClick={pop}
          className="w-16 h-16 rounded-full text-muted hover:bg-sunken text-2xl transition-all"
          aria-label="Delete"
        >
          ⌫
        </button>
      </div>
    </div>
  )
}
