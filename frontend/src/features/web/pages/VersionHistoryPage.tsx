import { Link } from 'react-router-dom'
import { Card } from '../../../components/Card'
import { PageHeader } from '../../../components/PageHeader'
import { APP_VERSION } from '../../../config/version'
import history from '../../../config/versionHistory.json'

const plainText = (value: string) => value.replace(/\*\*/g, '').replace(/`/g, '')

export function VersionHistoryPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <PageHeader title="Version history" icon="↺" subtitle="A readable record of how HomeStack has changed." />
      <p className="text-sm text-muted-strong">Installed version <strong className="text-ink">v{APP_VERSION}</strong></p>
      <div className="space-y-4">
        {history.releases.map(release => (
          <Card key={release.version}>
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-extrabold text-ink">v{release.version}</h2>
              <span className="text-xs font-semibold text-muted">{new Date(`${release.date}T00:00:00`).toLocaleDateString()} · {release.title}</span>
            </div>
            <ul className="space-y-1.5 text-sm text-muted-strong">
              {release.changes.map(change => <li key={change} className="flex gap-2"><span className="text-primary">•</span>{plainText(change)}</li>)}
            </ul>
          </Card>
        ))}
      </div>
      <Link to="/settings" className="font-bold text-primary hover:underline">← Manage HomeStack</Link>
    </div>
  )
}
