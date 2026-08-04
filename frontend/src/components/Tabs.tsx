import { useEffect, useRef } from 'react'

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
  const buttons = useRef<Array<HTMLButtonElement | null>>([])
  useEffect(() => {
    buttons.current[tabs.findIndex(tab => tab.key === active)]?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center',
    })
  }, [active])
  const moveFocus = (index: number, direction: number) => {
    const next = (index + direction + tabs.length) % tabs.length
    buttons.current[next]?.focus()
    onChange(tabs[next].key)
  }

  return (
    <div className={`tabs-scroll flex gap-1 rounded-2xl bg-sunken p-1 overflow-x-auto ${className}`} role="tablist">
      {tabs.map((t, index) => {
        const isActive = t.key === active
        return (
          <button
            key={t.key}
            ref={element => { buttons.current[index] = element }}
            onClick={() => onChange(t.key)}
            onKeyDown={event => {
              if (event.key === 'ArrowRight') { event.preventDefault(); moveFocus(index, 1) }
              if (event.key === 'ArrowLeft') { event.preventDefault(); moveFocus(index, -1) }
              if (event.key === 'Home') { event.preventDefault(); buttons.current[0]?.focus(); onChange(tabs[0].key) }
              if (event.key === 'End') { event.preventDefault(); buttons.current[tabs.length - 1]?.focus(); onChange(tabs[tabs.length - 1].key) }
            }}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            className={`flex min-h-[44px] items-center gap-1.5 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-semibold capitalize transition-colors sm:min-h-[40px] sm:px-3.5 ${
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
