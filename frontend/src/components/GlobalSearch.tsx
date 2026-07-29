import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { STACK_BY_KEY } from '../config/stacks'
import { Input } from './Field'
import { Modal } from './Modal'
import { InlineAlert } from './PageState'

interface SearchGroup {
  key: string
  label: string
  icon: string
  route: string
  matches: string[]
}

function group(key: string, query: string, matches: string[], route?: string): SearchGroup {
  const stack = STACK_BY_KEY[key]
  return {
    key,
    label: stack.label,
    icon: stack.icon,
    route: route || `${stack.route}?q=${encodeURIComponent(query)}`,
    matches: [...new Set(matches.filter(Boolean))].slice(0, 4),
  }
}

export function GlobalSearch({
  open,
  onClose,
  enabledKeys,
}: {
  open: boolean
  onClose: () => void
  enabledKeys: Set<string>
}) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchGroup[]>([])
  const [lockedNodes, setLockedNodes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const navMatches = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return []
    return Object.values(STACK_BY_KEY)
      .filter(stack => (!stack.isNode || enabledKeys.has(stack.key)) && stack.label.toLowerCase().includes(q))
      .map(stack => group(stack.key, query, [stack.label]))
  }, [enabledKeys, query])

  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus())
    else {
      setQuery('')
      setResults([])
      setLockedNodes([])
      setError('')
    }
  }, [open])

  useEffect(() => {
    const q = query.trim()
    if (!open || q.length < 2) {
      setResults([])
      setLoading(false)
      return
    }
    let active = true
    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const response = await api.globalSearch(q)
        if (!active) return
        const grouped = new Map<string, { matches: string[]; route: string }>()
        response.results.forEach(result => {
          const current = grouped.get(result.node) || { matches: [], route: result.route }
          current.matches.push(result.title)
          grouped.set(result.node, current)
        })
        setResults([...grouped.entries()]
          .filter(([key]) => Boolean(STACK_BY_KEY[key]))
          .map(([key, value]) => group(key, q, value.matches, value.route)))
        setLockedNodes(response.locked_nodes)
      } catch (searchError) {
        if (active) {
          setResults([])
          setLockedNodes([])
          setError(searchError instanceof Error ? searchError.message : 'Search could not be completed.')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }, 300)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [enabledKeys, open, query])

  if (!open) return null
  const merged = [...navMatches, ...results.filter(result => !navMatches.some(nav => nav.key === result.key))]

  const go = (route: string) => {
    navigate(route)
    onClose()
  }

  return (
    <Modal title="Search HomeStack" onClose={onClose} size="lg">
      <div className="space-y-4">
        <Input
          ref={inputRef}
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Search every enabled stack…"
          aria-label="Search HomeStack"
        />
        {loading && <div className="h-1 overflow-hidden rounded-full bg-sunken"><div className="h-full w-1/2 animate-pulse rounded-full bg-primary" /></div>}
        {error && <InlineAlert message={error} onDismiss={() => setError('')} />}
        {lockedNodes.includes('solace') && (
          <button onClick={() => go(`/solace?q=${encodeURIComponent(query)}`)} className="w-full rounded-xl bg-warning-soft px-3 py-2 text-left text-xs text-warning">
            Solace results are protected. Open Solace and enter your password to include them.
          </button>
        )}
        {query.trim().length < 2 ? (
          <p className="py-6 text-center text-sm text-muted">Type at least two characters. Press ⌘K or Ctrl K anytime to return here.</p>
        ) : merged.length === 0 && !loading ? (
          <p className="py-6 text-center text-sm text-muted">No matches across your enabled stacks.</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {merged.map(result => (
              <button
                key={result.key}
                onClick={() => go(result.route)}
                className="rounded-2xl border border-line bg-surface p-4 text-left transition-colors hover:bg-sunken"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xl">{result.icon}</span>
                  <span className="font-bold text-ink">{result.label}</span>
                  <span className="ml-auto text-xs text-muted">{result.matches.length} shown</span>
                </div>
                <p className="mt-2 truncate text-xs text-muted-strong">{result.matches.join(' · ')}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </Modal>
  )
}
