import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { QuickLaunchResolution } from '../../../api/types'
import { Button } from '../../../components/Button'
import { EmptyState } from '../../../components/EmptyState'

/**
 * The Quick Launch route contract: `/launch/<uuid>` (docs/39 §6).
 *
 * The point of the indirection is that nothing outside the server decides where a shortcut
 * goes. This page asks the API to resolve the shortcut *now* and then navigates to whatever it
 * says — so internal routes can change without breaking a saved or shared shortcut, and a
 * shortcut whose node was disabled, whose permission was withdrawn or whose record was deleted
 * lands on an honest "no longer available" instead of a stale path.
 *
 * A sensitive destination resolves to `locked`. The user is sent through the node's ordinary
 * unlock and returned here, so the destination they actually asked for is preserved rather than
 * dropping them on a node root.
 */
export function LaunchPage() {
  const { shortcutId = '' } = useParams()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [resolution, setResolution] = useState<QuickLaunchResolution | null>(null)
  const [failed, setFailed] = useState(false)
  const [removing, setRemoving] = useState(false)
  // Resolve exactly once per shortcut: re-running after the navigate would bounce the user back.
  const handled = useRef('')

  const run = useCallback(async () => {
    if (handled.current === shortcutId) return
    handled.current = shortcutId
    try {
      const result = await api.resolveQuickLaunchShortcut(shortcutId)
      setResolution(result)
      if (result.status === 'ok' && result.route) {
        const focused = result.launch_mode === 'focused'
        navigate(
          focused ? `${result.route}${result.route.includes('?') ? '&' : '?'}focus=1` : result.route,
          { replace: true },
        )
      }
    } catch {
      // A missing shortcut and someone else's shortcut fail identically by design.
      setFailed(true)
    }
  }, [navigate, shortcutId])

  useEffect(() => { void run() }, [run])

  const remove = async () => {
    setRemoving(true)
    try { await api.deleteQuickLaunchShortcut(shortcutId) } catch { /* already gone */ }
    navigate('/settings/quick-launch', { replace: true })
  }

  if (!resolution && !failed) {
    return (
      <div className="grid min-h-[14rem] place-items-center" aria-live="polite">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <span className="sr-only">Opening your shortcut…</span>
      </div>
    )
  }

  // Temporarily locked rather than gone: send them through the node's own unlock, which returns
  // here and completes the original journey.
  if (resolution?.status === 'locked' && resolution.route) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
        <EmptyState
          icon="🔒"
          title={resolution.label || 'Locked'}
          hint="This area asks for your password before it opens."
        />
        <Button
          onClick={() => navigate(resolution.route!, { replace: true })}
          className="self-center"
        >
          Unlock and continue
        </Button>
        <Link to="/hub" className="text-center text-sm font-semibold text-primary hover:underline">
          Back to HomeStack
        </Link>
      </div>
    )
  }

  const reason = resolution?.reason || 'This shortcut is no longer available.'
  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <EmptyState
        icon="🧭"
        title="This shortcut is no longer available."
        hint={
          params.get('from') === 'list'
            ? reason
            : `${reason} The thing it pointed at may have been removed, or you may no longer have access to it.`
        }
      />
      <div className="flex flex-wrap justify-center gap-2">
        <Button variant="ghost" onClick={remove} loading={removing}>Remove shortcut</Button>
        <Button onClick={() => navigate('/hub', { replace: true })}>Back to HomeStack</Button>
      </div>
    </div>
  )
}
