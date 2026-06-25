import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { TasksTab } from './meridian/TasksTab'
import { ShopTab } from './meridian/ShopTab'
import { RoutinesTab } from './meridian/RoutinesTab'
import { GoalsTab, WishlistTab } from './meridian/GoalsWishlistTabs'
import { LeaderboardTab, SettingsTab } from './meridian/ReportsSettingsTabs'

type Tab = 'tasks' | 'routines' | 'shop' | 'goals' | 'wishlist' | 'leaderboard' | 'settings'

export function MeridianPage() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'manager'
  const [tab, setTab] = useState<Tab>('tasks')
  const [pointsLabel, setPointsLabel] = useState('points')

  useEffect(() => {
    api.getMeridianSettings().then(s => setPointsLabel(s.points_label || 'points')).catch(() => {})
  }, [])

  const tabs: Tab[] = ['tasks', 'routines', 'shop', 'goals', 'wishlist', 'leaderboard']
  if (canManage) tabs.push('settings')

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">Meridian</h1>

      <div className="flex flex-wrap gap-1 bg-sunken p-1 rounded-xl w-fit">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors capitalize ${
              tab === t ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

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
