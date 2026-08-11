import { Link, Navigate, useParams } from 'react-router-dom'
import { Card } from '../../../components/Card'
import { PageHeader } from '../../../components/PageHeader'
import { NODE_GUIDE_BY_KEY, fallbackNodeGuide } from '../../../config/nodeGuides'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { useStacks } from '../../stacks/StacksContext'

export function NodeGuidePage() {
  const { nodeKey = '' } = useParams()
  const { nodes } = useStacks()
  const node = nodes.find(candidate => candidate.key === nodeKey)
  const guide = NODE_GUIDE_BY_KEY[nodeKey] ?? (node ? fallbackNodeGuide(node) : null)
  if (!guide) return <Navigate to="/settings" replace />

  const stack = STACK_BY_KEY[nodeKey]
  const enabled = !stack?.isNode || Boolean(node?.is_enabled && !node.is_hidden)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <PageHeader title={`${guide.label} guide`} icon={guide.icon} subtitle={guide.summary} />
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${enabled ? 'bg-success-soft text-success' : 'bg-sunken text-muted-strong'}`}>
          {enabled ? 'Available now' : 'Currently disabled'}
        </span>
        {enabled && stack && <Link to={stack.route} className="text-sm font-bold text-primary hover:underline">Open {guide.label} →</Link>}
        {!enabled && <Link to="/settings" className="text-sm font-bold text-primary hover:underline">Manage nodes →</Link>}
      </div>

      <Card title="What it does">
        <p className="leading-7 text-muted-strong">{guide.purpose}</p>
      </Card>

      <div className="grid gap-5 md:grid-cols-2">
        <Card title="Getting started">
          <ol className="space-y-3">
            {guide.gettingStarted.map((item, index) => (
              <li key={item} className="flex gap-3 text-sm text-muted-strong">
                <span className="grid h-6 w-6 flex-shrink-0 place-items-center rounded-full text-xs font-extrabold" style={{ background: softColour(guide.colour, '20'), color: guide.colour }}>{index + 1}</span>
                <span className="pt-0.5">{item}</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="What you can manage">
          {guide.capabilities.length ? (
            <ul className="space-y-2 text-sm text-muted-strong">
              {guide.capabilities.map(item => <li key={item} className="flex gap-2"><span className="text-success">✓</span>{item}</li>)}
            </ul>
          ) : <p className="text-sm text-muted">More detailed guidance will be added as this node develops.</p>}
        </Card>
      </div>

      <Card title="How it works with HomeStack">
        <ul className="space-y-2 text-sm text-muted-strong">
          {guide.connections.map(item => <li key={item} className="flex gap-2"><span style={{ color: guide.colour }}>↗</span>{item}</li>)}
        </ul>
      </Card>

      <div className="flex justify-between border-t border-line pt-4 text-sm">
        <Link to="/settings" className="font-bold text-primary hover:underline">← Manage HomeStack</Link>
        <Link to="/settings/version-history" className="font-bold text-muted-strong hover:text-primary">Version history</Link>
      </div>
    </div>
  )
}
