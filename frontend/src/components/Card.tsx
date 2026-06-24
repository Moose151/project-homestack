import type { ReactNode } from 'react'

interface Props {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = '' }: Props) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 ${className}`}>
      {title && (
        <div className="px-5 pt-4 pb-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">{title}</h3>
        </div>
      )}
      <div className="p-5 pt-3">{children}</div>
    </div>
  )
}
