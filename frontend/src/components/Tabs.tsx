export interface TabDef<T extends string = string> {
  key: T
  label: string
  /** optional count/badge shown after the label */
  badge?: number | string
}

/** Shared segmented tab control used by every node's page (Atlas, Meridian, Education, …). */
export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
  className = '',
}: {
  tabs: TabDef<T>[]
  active: T
  onChange: (key: T) => void
  className?: string
}) {
  return (
    <div className={`flex gap-1 rounded-2xl bg-sunken p-1 overflow-x-auto ${className}`}>
      {tabs.map(t => {
        const isActive = t.key === active
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold capitalize transition-colors ${
              isActive ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
            }`}
          >
            {t.label}
            {t.badge !== undefined && t.badge !== 0 && (
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none ${
                  isActive ? 'bg-primary/15 text-primary' : 'bg-line text-muted-strong'
                }`}
              >
                {t.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
