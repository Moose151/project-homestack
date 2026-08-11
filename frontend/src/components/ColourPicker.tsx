export const HOME_COLOURS = [
  '#B91C1C', '#DC2626', '#EA580C', '#D97706', '#CA8A04', '#65A30D',
  '#16A34A', '#059669', '#0D9488', '#0891B2', '#0284C7', '#2563EB',
  '#4F46E5', '#7C3AED', '#9333EA', '#C026D3', '#DB2777', '#E11D48',
  '#B0563C', '#8F4E38', '#7C6F5A', '#64748B', '#475569', '#1F2937',
] as const

export function ColourPicker({ value, onChange, allowClear = false, ariaLabel = 'Choose colour' }: {
  value: string
  onChange: (colour: string) => void
  allowClear?: boolean
  ariaLabel?: string
}) {
  const current = (value || '').toUpperCase()
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label={ariaLabel}>
        {HOME_COLOURS.map(colour => (
          <button
            key={colour}
            type="button"
            onClick={() => onChange(colour)}
            aria-label={`Use colour ${colour}`}
            aria-pressed={current === colour}
            className={`h-8 w-8 rounded-full border-2 shadow-sm transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary/50 ${current === colour ? 'border-ink ring-2 ring-surface ring-offset-1 ring-offset-ink' : 'border-surface'}`}
            style={{ backgroundColor: colour }}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex min-h-10 items-center gap-2 rounded-xl border border-line bg-surface px-2.5 text-xs font-semibold text-muted-strong">
          <input type="color" value={value || '#64748B'} onChange={event => onChange(event.target.value.toUpperCase())} className="h-7 w-8 cursor-pointer border-0 bg-transparent p-0" aria-label="Custom colour" />
          Custom
        </label>
        {value && <span className="font-mono text-xs text-muted">{value.toUpperCase()}</span>}
        {allowClear && value && <button type="button" onClick={() => onChange('')} className="min-h-9 rounded-lg px-2 text-xs font-bold text-muted hover:bg-sunken hover:text-danger">Use automatic colour</button>}
      </div>
    </div>
  )
}
