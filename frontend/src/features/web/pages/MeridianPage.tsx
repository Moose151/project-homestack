import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { SearchField } from '../../../components/Field'
import { MobileListRow, MobileScreenHeader, MobileSection } from '../../../components/mobile'

type Tab = 'overview' | 'tasks' | 'routines' | 'shop' | 'goals' | 'wishlist' | 'leaderboard' | 'settings'
const TAB_KEYS: Tab[] = ['overview', 'tasks', 'routines', 'shop', 'goals', 'wishlist', 'leaderboard', 'settings']

// docs/36 §6.4: phone gets "Tasks / Rewards / My progress / More" instead of navigating the flat
// eight-tab picker. Tasks folds in Routines and My progress folds in Goals/Wishlist/Leaderboard —
// each keeps a small secondary switcher once inside the group. `?tab=` stays the single source of
// truth for both desktop and phone, so every existing deep link (Hub, Corners, source links) is
// untouched — the grouping is purely a phone-side presentation layer over the same tab state.
type Group = 'tasks' | 'rewards' | 'progress' | 'more'
const GROUP_FOR_TAB: Partial<Record<Tab, Group>> = {
  tasks: 'tasks', routines: 'tasks', shop: 'rewards',
  goals: 'progress', wishlist: 'progress', leaderboard: 'progress', settings: 'more',
}
const GROUP_TITLE: Record<Group, string> = { tasks: 'Tasks', rewards: 'Rewards', progress: 'My progress', more: 'Manage' }

export function MeridianPage() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'manager'
  const [tab, setTab] = useUrlTab<Tab>('overview', TAB_KEYS)
  const [searchParams] = useSearchParams()
  const focusedTaskId = Number(searchParams.get('task') || 0)
  const focusedWishId = Number(searchParams.get('wish') || 0)
  const [pointsLabel, setPointsLabel] = useState('points')
  const [query, setQuery] = useUrlQueryState()

  useEffect(() => {
    api.getMeridianSettings().then(s => setPointsLabel(s.points_label || 'points')).catch(() => {})
  }, [])

  const tabKeys: Tab[] = ['overview', 'tasks', 'routines', 'shop', 'goals', 'wishlist', 'leaderboard']
  if (canManage) tabKeys.push('settings')
  // "Manage" everywhere a node has a setup tab, so the same job is not called two things in
  // two destinations. The key stays `settings` so existing links keep working.
  const tabs: TabDef<Tab>[] = tabKeys.map(t => ({ key: t, label: t === 'settings' ? 'manage' : t }))
  const group = GROUP_FOR_TAB[tab]

  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      <div className="hidden sm:block">
        <PageHeader
          title="Tasks & rewards"
          icon="⭐"
        />
      </div>

      <SearchField value={query} onChange={event => setQuery(event.target.value)} onClear={() => setQuery('')} placeholder="Search tasks and rewards…" />

      <div className="hidden sm:block">
        <Tabs tabs={tabs} active={tab} onChange={setTab} className="w-fit" />
      </div>

      {tab === 'overview' ? (
        <div className="flex flex-col gap-4 sm:hidden">
          <OverviewTab
            canManage={canManage}
            pointsLabel={pointsLabel}
            onOpenTasks={() => setTab('tasks')}
            onOpenShop={() => setTab('shop')}
          />
          <MobileSection title="Sections">
            <MobileListRow icon="✅" title="Tasks" subtitle="Ordinary tasks and routines" onClick={() => setTab('tasks')} />
            <MobileListRow icon="🎁" title="Rewards" subtitle="Shop and redemptions" onClick={() => setTab('shop')} />
            <MobileListRow icon="📈" title="My progress" subtitle="Goals, wishlist and leaderboard" onClick={() => setTab('goals')} />
            {canManage && <MobileListRow icon="⚙️" title="Manage" subtitle="Setup and settings" onClick={() => setTab('settings')} />}
          </MobileSection>
        </div>
      ) : (
        group && (
          <div className="sm:hidden">
            <MobileScreenHeader title={GROUP_TITLE[group]} showBack onBack={() => setTab('overview')} />
            {group === 'tasks' && (
              <Tabs
                variant="secondary"
                className="mt-3"
                tabs={[{ key: 'tasks', label: 'Tasks' }, { key: 'routines', label: 'Routines' }]}
                active={tab === 'routines' ? 'routines' : 'tasks'}
                onChange={setTab}
              />
            )}
            {group === 'progress' && (
              <Tabs
                variant="secondary"
                className="mt-3"
                tabs={[{ key: 'goals', label: 'Goals' }, { key: 'wishlist', label: 'Wishlist' }, { key: 'leaderboard', label: 'Leaderboard' }]}
                active={tab === 'wishlist' || tab === 'leaderboard' ? tab : 'goals'}
                onChange={setTab}
              />
            )}
          </div>
        )
      )}

      {tab === 'overview' && (
        <div className="hidden sm:block">
          <OverviewTab
            canManage={canManage}
            pointsLabel={pointsLabel}
            onOpenTasks={() => setTab('tasks')}
            onOpenShop={() => setTab('shop')}
          />
        </div>
      )}
      {tab === 'tasks' && <TasksTab canManage={canManage} pointsLabel={pointsLabel} searchQuery={query} focusedTaskId={focusedTaskId || undefined} />}
      {tab === 'routines' && <RoutinesTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'shop' && <ShopTab canManage={canManage} pointsLabel={pointsLabel} searchQuery={query} />}
      {tab === 'goals' && <GoalsTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'wishlist' && <WishlistTab canManage={canManage} pointsLabel={pointsLabel} focusedWishId={focusedWishId || undefined} />}
      {tab === 'leaderboard' && <LeaderboardTab pointsLabel={pointsLabel} />}
      {tab === 'settings' && canManage && <SettingsTab />}
    </div>
  )
}
