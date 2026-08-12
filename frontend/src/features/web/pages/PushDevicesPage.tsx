import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { HouseholdPushDeviceGroup } from '../../../api/types'
import { Card } from '../../../components/Card'
import { PageHeader } from '../../../components/PageHeader'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'
import { deviceDetail, lastSeenLabel } from './pushDeviceFormat'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const ROLE_LABEL: Record<string, string> = {
  admin: 'Administrator', manager: 'Household manager', user: 'Household member', guest: 'Guest',
}

/**
 * Admin-only overview of who in the household is set up for push, on what.
 *
 * Deliberately read-only: this answers the operational question ("is Partner's phone actually
 * registered? is that tablet still in use?") without letting one login rename or test another
 * person's device. Owners manage their own devices from their notification settings.
 */
export function PushDevicesPage() {
  const [groups, setGroups] = useState<HouseholdPushDeviceGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getHouseholdPushDevices()
      .then(setGroups)
      .catch(e => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [])

  const deviceCount = groups.reduce((total, group) => total + group.devices.length, 0)

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <PageHeader
        title="Push devices"
        icon="📱"
        subtitle="Every household device currently registered for push notifications."
      />

      {error && <InlineAlert tone="danger" message={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <PageSkeleton />
      ) : groups.length === 0 ? (
        <Card title="No devices registered">
          <p className="text-sm text-muted">
            Nobody has enabled push yet. Each person enables it themselves from
            Manage HomeStack → Your notifications, on each device they want notified.
          </p>
        </Card>
      ) : (
        <Card title={`${deviceCount} device${deviceCount === 1 ? '' : 's'} across ${groups.length} ${groups.length === 1 ? 'person' : 'people'}`}>
          <div className="space-y-5">
            {groups.map(group => (
              <div key={group.user_id}>
                <div className="mb-2 flex items-baseline gap-2">
                  <h3 className="text-sm font-bold text-ink">{group.user_display_name}</h3>
                  <span className="text-xs text-muted">{ROLE_LABEL[group.user_role] ?? group.user_role}</span>
                </div>
                <ul className="space-y-2">
                  {group.devices.map(device => (
                    <li
                      key={device.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-3 py-2"
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-ink">{device.label || 'Device'}</div>
                        <div className="text-xs text-muted">{deviceDetail(device) || 'Unknown browser'}</div>
                      </div>
                      <span className="text-xs text-muted">Last seen {lastSeenLabel(device.last_seen_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-muted">
            Devices are named by the person who registered them. Revoking a device is done by its
            owner from their own notification settings.
          </p>
        </Card>
      )}

      <Link to="/settings" className="font-bold text-primary hover:underline">← Manage HomeStack</Link>
    </div>
  )
}
