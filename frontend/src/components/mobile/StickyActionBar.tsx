import type { ReactNode } from 'react'

/**
 * Safe-area-aware bottom action bar (docs/36 §5, §3.3: "avoid primary actions being covered by
 * the fixed bottom navigation"). Fixed just above the app shell's bottom nav on phone; a plain
 * static bar on desktop, where there is no bottom nav to clear. The `6.25rem` offset clears the
 * inset floating dock and its raised Add control, and matches other fixed-above-nav controls.
 */
export function StickyActionBar({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`fixed inset-x-0 bottom-[calc(6.25rem+env(safe-area-inset-bottom))] z-20 mx-auto flex w-full max-w-[calc(100%-2rem)] items-center gap-2 rounded-2xl border border-line bg-surface/95 p-2.5 shadow-card backdrop-blur-xl md:static md:bottom-auto md:w-full md:max-w-none md:border-t md:border-x-0 md:border-b-0 md:rounded-none md:bg-surface md:p-4 md:shadow-none md:backdrop-blur-none ${className}`}
    >
      {children}
    </div>
  )
}
