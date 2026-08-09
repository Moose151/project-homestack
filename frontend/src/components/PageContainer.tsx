import type { ReactNode } from 'react'

/**
 * The one content column for the whole app.
 *
 * Pages used to set their own `max-w-5xl` / `max-w-7xl` / nothing, so the content box moved
 * by hundreds of pixels every time you changed destination. Everything that sits in the
 * content area — the top bar's title block, `<main>`, and each page — uses these classes so
 * the left edge and the line length are identical everywhere.
 *
 * Change the width here and it changes once, for every surface.
 */
export const CONTENT_CONTAINER = 'mx-auto w-full max-w-[1400px] px-4 sm:px-5 md:px-7 lg:px-9'

export function PageContainer({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`${CONTENT_CONTAINER} ${className}`}>{children}</div>
}
