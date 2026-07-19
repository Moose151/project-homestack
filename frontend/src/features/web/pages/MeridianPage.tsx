import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { TasksTab } from './meridian/TasksTab'
import { ShopTab } from './meridian/ShopTab'
import { RoutinesTab } from './meridian/RoutinesTab'
import { GoalsTab, WishlistTab } from './meridian/GoalsWishlistTabs'
import { LeaderboardTab, SettingsTab } from './meridian/ReportsSettingsTabs'
import { OverviewTab } from './meridian/OverviewTab'
import { PageHeader } from '../../../components/PageHeader'
import { Tabs, type TabDef } from '../../../components/Tabs'

type Tab = 'overview' | 'tasks' | 'routines' | 'shop' | 'goals' | 'wishlist' | 'leaderboard' | 'settings'

export function MeridianPage() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'manager'
  const [tab, setTab] = useState<Tab>('overview')
  const [pointsLabel, setPointsLabel] = useState('points')

  useEffect(() => {
    api.getMeridianSettings().then(s => setPointsLabel(s.points_label || 'points')).catch(() => {})
  }, [])

  const tabKeys: Tab[] = ['overview', 'tasks', 'routines', 'shop', 'goals', 'wishlist', 'leaderboard']
  if (canManage) tabKeys.push('settings')
  const tabs: TabDef<Tab>[] = tabKeys.map(t => ({ key: t, label: t }))

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Meridian"
        icon="⭐"
        subtitle="Approvals, setup and household progress for the Meridian points system."
      />

      <Tabs tabs={tabs} active={tab} onChange={setTab} className="w-fit" />

      {tab === 'overview' && (
        <OverviewTab
          canManage={canManage}
          pointsLabel={pointsLabel}
          onOpenTasks={() => setTab('tasks')}
          onOpenShop={() => setTab('shop')}
        />
      )}
      {tab === 'tasks' && <TasksTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'routines' && <RoutinesTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'shop' && <ShopTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'goals' && <GoalsTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'wishlist' && <WishlistTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'leaderboard' && <LeaderboardTab pointsLabel={pointsLabel} />}
      {tab === 'settings' && canManage && <SettingsTab />}
    </div>
  )
}
