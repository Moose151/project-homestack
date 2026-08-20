import { type ReactNode, useId } from 'react'

/**
 * A single expand/collapse settings-style row: icon, title, subtitle and a rotating chevron,
 * with its content revealed directly beneath it. The whole header is one clickable/keyboard
 * button (not just the chevron — WCAG 2.5.5), and the panel is only mounted while open so a
 * collapsed section never leaves hidden-but-tabbable fields behind. Grid-row animation (rather
 * than max-height) means the expand/collapse transition is smooth regardless of content height.
 */
export function AccordionItem({
  icon, title, subtitle, isOpen, onToggle, children, className = '',
}: {
  icon?: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  isOpen: boolean
  onToggle: () => void
  children: ReactNode
  className?: string
}) {
  const reactId = useId()
  const buttonId = `accordion-button-${reactId}`
  const panelId = `accordion-panel-${reactId}`

  return (
    <div className={`overflow-hidden rounded-2xl border border-line bg-surface shadow-soft ${className}`}>
      <h3 className="contents">
        <button
          type="button"
          id={buttonId}
          aria-expanded={isOpen}
          aria-controls={panelId}
          onClick={onToggle}
          className="flex min-h-[44px] w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-sunken focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary sm:px-4"
        >
          {icon && (
            <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl bg-sunken text-xl leading-none">
              {icon}
            </span>
          )}
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[15px] font-semibold text-ink">{title}</span>
            {subtitle && <span className="block truncate text-sm text-muted">{subtitle}</span>}
          </span>
          <span
            aria-hidden="true"
            className={`flex-shrink-0 text-lg text-muted transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
          >
            ›
          </span>
        </button>
      </h3>
      <div
        id={panelId}
        className="grid transition-[grid-template-rows] duration-200 ease-out"
        style={{ gridTemplateRows: isOpen ? '1fr' : '0fr' }}
      >
        <div className="min-h-0 overflow-hidden">
          {isOpen && (
            <div className="border-t border-line px-3 pb-4 pt-3 sm:px-4">
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
