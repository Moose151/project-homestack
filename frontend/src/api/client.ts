import type {
  AtlasList, AtlasListItem, AtlasNote, AtlasReminder,
  AuthUser, CalendarEvent, CalendarEventWrite, HubResponse, HubWidgetConfig, KioskUser,
  KioskMeridian, MeridianPointsResponse, MeridianReward,
  MeridianRewardRequest, MeridianTask, MeridianTaskCompletion,
  MeridianCategory, MeridianRoutine, MeridianGoal,
  MeridianWishlistItem, MeridianWishlistRequest, MeridianSettings,
  MeridianReports, Badge, PersonBadge, NotificationList, Person, AdminUser,
  AtlasSearchResults,
} from './types'

type ItemWrite = Partial<{
  title: string; notes: string; quantity: string; position: number
  due_at: string | null; assigned_to_person_id: number | null
}>

type UserWrite = Partial<{
  username: string; display_name: string; role: string; email: string; colour: string
  avatar: string; is_child_account: boolean; is_active: boolean; pin: string; password: string
  link_person_id: number | null; create_person: boolean
}>

const BASE = '/api/v1'

// Django/DRF SessionAuthentication enforces CSRF on unsafe methods. The token is
// delivered in the `csrftoken` cookie (set by the GET /auth/me/ call on app load)
// and must be echoed back in the X-CSRFToken header on every write.
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

async function _fetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase()
  const csrfHeader: Record<string, string> = {}
  if (!SAFE_METHODS.has(method)) {
    const token = getCookie('csrftoken')
    if (token) csrfHeader['X-CSRFToken'] = token
  }
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...csrfHeader, ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // --- Auth ---
  getKioskUsers: (): Promise<KioskUser[]> => _fetch('/auth/kiosk-users/'),
  pinLogin: (username: string, pin: string): Promise<AuthUser> =>
    _fetch('/auth/pin-login/', { method: 'POST', body: JSON.stringify({ username, pin }) }),
  passwordLogin: (username: string, password: string): Promise<AuthUser> =>
    _fetch('/auth/password-login/', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: (): Promise<void> => _fetch('/auth/logout/', { method: 'POST' }),
  me: (): Promise<AuthUser> => _fetch('/auth/me/'),
  reauth: (password: string): Promise<void> =>
    _fetch('/auth/reauth/', { method: 'POST', body: JSON.stringify({ password }) }),

  // --- People ---
  getPeople: (): Promise<Person[]> => _fetch('/people/'),

  // --- User management (admin) ---
  getUsers: (): Promise<AdminUser[]> => _fetch('/users/'),
  createUser: (data: UserWrite): Promise<AdminUser> =>
    _fetch('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: number, data: UserWrite): Promise<AdminUser> =>
    _fetch(`/users/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deactivateUser: (id: number): Promise<void> =>
    _fetch(`/users/${id}/`, { method: 'DELETE' }),

  // --- Hub ---
  hub: (): Promise<HubResponse> => _fetch('/hub/'),
  kioskHub: (): Promise<HubResponse> => _fetch('/hub/kiosk/'),
  getHubWidgetConfig: (): Promise<{ widgets: HubWidgetConfig[] }> => _fetch('/hub/widgets/'),
  setHouseholdWidget: (key: string, data: Partial<{ is_enabled: boolean; display_order: number; size: string }>):
    Promise<{ widgets: HubWidgetConfig[] }> =>
    _fetch(`/hub/widgets/${key}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  setUserWidget: (key: string, data: Partial<{ is_enabled: boolean; display_order: number }>):
    Promise<{ widgets: HubWidgetConfig[] }> =>
    _fetch(`/hub/widgets/${key}/me/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // --- Atlas lists ---
  getLists: (): Promise<AtlasList[]> => _fetch('/atlas/lists/'),
  getList: (id: number): Promise<AtlasList> => _fetch(`/atlas/lists/${id}/`),
  createList: (data: { title: string; list_type: string; visibility?: string }): Promise<AtlasList> =>
    _fetch('/atlas/lists/', { method: 'POST', body: JSON.stringify(data) }),
  deleteList: (id: number): Promise<void> => _fetch(`/atlas/lists/${id}/`, { method: 'DELETE' }),

  // --- Atlas list items ---
  createItem: (listId: number, data: ItemWrite): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/`, { method: 'POST', body: JSON.stringify(data) }),
  updateItem: (listId: number, itemId: number, data: ItemWrite): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  completeItem: (listId: number, itemId: number): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/complete/`, { method: 'POST' }),
  uncompleteItem: (listId: number, itemId: number): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/uncomplete/`, { method: 'POST' }),
  deleteItem: (listId: number, itemId: number): Promise<void> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/`, { method: 'DELETE' }),

  // --- Atlas search ---
  searchAtlas: (q: string): Promise<AtlasSearchResults> =>
    _fetch(`/atlas/search/?q=${encodeURIComponent(q)}`),

  // --- Atlas notes ---
  getNotes: (): Promise<AtlasNote[]> => _fetch('/atlas/notes/'),
  createNote: (data: { title: string; body?: string }): Promise<AtlasNote> =>
    _fetch('/atlas/notes/', { method: 'POST', body: JSON.stringify(data) }),
  deleteNote: (id: number): Promise<void> => _fetch(`/atlas/notes/${id}/`, { method: 'DELETE' }),

  // --- Atlas reminders ---
  getReminders: (upcoming?: boolean): Promise<AtlasReminder[]> =>
    _fetch(`/atlas/reminders/${upcoming ? '?upcoming=1' : ''}`),
  createReminder: (data: { title: string; due_at?: string; body?: string }): Promise<AtlasReminder> =>
    _fetch('/atlas/reminders/', { method: 'POST', body: JSON.stringify(data) }),
  deleteReminder: (id: number): Promise<void> => _fetch(`/atlas/reminders/${id}/`, { method: 'DELETE' }),

  // --- Calendar ---
  getEvents: (params?: { start?: string; end?: string; node?: string; person?: number; upcoming?: boolean }): Promise<CalendarEvent[]> => {
    const q = new URLSearchParams()
    if (params?.start) q.set('start', params.start)
    if (params?.end) q.set('end', params.end)
    if (params?.node) q.set('node', params.node)
    if (params?.person) q.set('person', String(params.person))
    if (params?.upcoming) q.set('upcoming', '1')
    const s = q.toString()
    return _fetch(`/calendar/events/${s ? `?${s}` : ''}`)
  },
  createEvent: (data: CalendarEventWrite): Promise<CalendarEvent> =>
    _fetch('/calendar/events/', { method: 'POST', body: JSON.stringify(data) }),
  updateEvent: (id: number, data: Partial<CalendarEventWrite>): Promise<CalendarEvent> =>
    _fetch(`/calendar/events/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteEvent: (id: number): Promise<void> =>
    _fetch(`/calendar/events/${id}/`, { method: 'DELETE' }),

  // --- Meridian: tasks ---
  getMeridianTasks: (params?: { status?: string; hot?: boolean }): Promise<MeridianTask[]> => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.hot) q.set('hot', '1')
    const s = q.toString()
    return _fetch(`/meridian/tasks/${s ? `?${s}` : ''}`)
  },
  createMeridianTask: (data: {
    title: string; points: number; description?: string
    assigned_to_person_id?: number | null; is_hot?: boolean; due_at?: string
    hot_bonus_points?: number; hot_label?: string; category_id?: number | null
    completion_behavior?: string; completion_scope?: string; availability_window?: string
  }): Promise<MeridianTask> =>
    _fetch('/meridian/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  deleteMeridianTask: (id: number): Promise<void> =>
    _fetch(`/meridian/tasks/${id}/`, { method: 'DELETE' }),
  completeMeridianTask: (id: number, personId?: number): Promise<MeridianTask> =>
    _fetch(`/meridian/tasks/${id}/complete/`, {
      method: 'POST', body: JSON.stringify(personId ? { person_id: personId } : {}),
    }),
  approveMeridianTask: (id: number): Promise<MeridianTask> =>
    _fetch(`/meridian/tasks/${id}/approve/`, { method: 'POST' }),
  rejectMeridianTask: (id: number, reason?: string): Promise<MeridianTask> =>
    _fetch(`/meridian/tasks/${id}/reject/`, { method: 'POST', body: JSON.stringify({ reason }) }),
  getMeridianTaskCompletions: (params?: {
    status?: 'submitted' | 'approved' | 'rejected'; taskId?: number; personId?: number
  }): Promise<MeridianTaskCompletion[]> => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.taskId) q.set('task_id', String(params.taskId))
    if (params?.personId) q.set('person_id', String(params.personId))
    const s = q.toString()
    return _fetch(`/meridian/task-completions/${s ? `?${s}` : ''}`)
  },
  approveMeridianTaskCompletion: (id: number, reviewNote?: string): Promise<MeridianTaskCompletion> =>
    _fetch(`/meridian/task-completions/${id}/approve/`, {
      method: 'POST', body: JSON.stringify({ review_note: reviewNote || '' }),
    }),
  rejectMeridianTaskCompletion: (id: number, reason?: string, reviewNote?: string): Promise<MeridianTaskCompletion> =>
    _fetch(`/meridian/task-completions/${id}/reject/`, {
      method: 'POST', body: JSON.stringify({ reason: reason || '', review_note: reviewNote || '' }),
    }),

  // --- Meridian: points ---
  getMeridianPoints: (): Promise<MeridianPointsResponse> => _fetch('/meridian/points/'),

  // --- Meridian: rewards ---
  getMeridianRewards: (activeOnly?: boolean): Promise<MeridianReward[]> =>
    _fetch(`/meridian/rewards/${activeOnly ? '?active=1' : ''}`),
  createMeridianReward: (data: {
    name: string; cost_points: number; description?: string
  }): Promise<MeridianReward> =>
    _fetch('/meridian/rewards/', { method: 'POST', body: JSON.stringify(data) }),
  updateMeridianReward: (id: number, data: Partial<{
    name: string; description: string; cost_points: number; category_id: number | null
    icon: string; colour: string
    image_url: string; is_active: boolean; is_archived: boolean; price_estimate: string
    store_url: string; quantity: number | null; allow_multiple_in_cart: boolean
    disappear_when_empty: boolean; daily_limit_per_user: number | null
  }>): Promise<MeridianReward> =>
    _fetch(`/meridian/rewards/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteMeridianReward: (id: number): Promise<void> =>
    _fetch(`/meridian/rewards/${id}/`, { method: 'DELETE' }),
  requestMeridianReward: (id: number, personId?: number): Promise<MeridianRewardRequest> =>
    _fetch(`/meridian/rewards/${id}/request/`, {
      method: 'POST', body: JSON.stringify(personId ? { person_id: personId } : {}),
    }),

  // --- Meridian: reward requests ---
  getMeridianRewardRequests: (status?: string): Promise<MeridianRewardRequest[]> =>
    _fetch(`/meridian/reward-requests/${status ? `?status=${status}` : ''}`),
  approveMeridianRewardRequest: (id: number): Promise<MeridianRewardRequest> =>
    _fetch(`/meridian/reward-requests/${id}/approve/`, { method: 'POST' }),
  rejectMeridianRewardRequest: (id: number, reason?: string): Promise<MeridianRewardRequest> =>
    _fetch(`/meridian/reward-requests/${id}/reject/`, { method: 'POST', body: JSON.stringify({ reason }) }),

  updateMeridianTask: (id: number, data: Partial<{
    title: string; description: string; points: number; category_id: number | null
    assigned_to_person_id: number | null; is_hot: boolean; hot_bonus_points: number
    hot_label: string; completion_behavior: string; due_at: string | null
    completion_scope: string; recurrence_rule: string; visibility: string
    is_active: boolean; is_archived: boolean
  }>): Promise<MeridianTask> =>
    _fetch(`/meridian/tasks/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // --- Meridian: routines ---
  getMeridianRoutines: (personId?: number): Promise<MeridianRoutine[]> =>
    _fetch(`/meridian/routines/${personId ? `?person_id=${personId}` : ''}`),
  createMeridianRoutine: (data: {
    title: string; points: number; description?: string; assigned_to_person_id?: number | null
  }): Promise<MeridianRoutine> =>
    _fetch('/meridian/routines/', { method: 'POST', body: JSON.stringify(data) }),
  deleteMeridianRoutine: (id: number): Promise<void> =>
    _fetch(`/meridian/routines/${id}/`, { method: 'DELETE' }),
  completeMeridianRoutine: (id: number, personId?: number): Promise<MeridianRoutine> =>
    _fetch(`/meridian/routines/${id}/complete/`, {
      method: 'POST', body: JSON.stringify(personId ? { person_id: personId } : {}),
    }),

  // --- Meridian: categories ---
  getMeridianCategories: (kind?: 'task' | 'reward'): Promise<MeridianCategory[]> =>
    _fetch(`/meridian/categories/${kind ? `?kind=${kind}` : ''}`),
  createMeridianCategory: (data: { name: string; kind: string; colour?: string; icon?: string }): Promise<MeridianCategory> =>
    _fetch('/meridian/categories/', { method: 'POST', body: JSON.stringify(data) }),
  deleteMeridianCategory: (id: number): Promise<void> =>
    _fetch(`/meridian/categories/${id}/`, { method: 'DELETE' }),

  // --- Meridian: shop cart ---
  checkoutCart: (rewardIds: number[], personId?: number): Promise<MeridianRewardRequest[]> =>
    _fetch('/meridian/rewards/checkout/', {
      method: 'POST',
      body: JSON.stringify({ reward_ids: rewardIds, ...(personId ? { person_id: personId } : {}) }),
    }),

  // --- Meridian: group goals ---
  getMeridianGoals: (activeOnly?: boolean): Promise<MeridianGoal[]> =>
    _fetch(`/meridian/goals/${activeOnly ? '?active=1' : ''}`),
  createMeridianGoal: (data: { title: string; target_points: number; description?: string }): Promise<MeridianGoal> =>
    _fetch('/meridian/goals/', { method: 'POST', body: JSON.stringify(data) }),
  deleteMeridianGoal: (id: number): Promise<void> =>
    _fetch(`/meridian/goals/${id}/`, { method: 'DELETE' }),
  contributeToGoal: (id: number, amount: number, personId?: number): Promise<MeridianGoal> =>
    _fetch(`/meridian/goals/${id}/contribute/`, {
      method: 'POST', body: JSON.stringify({ amount, ...(personId ? { person_id: personId } : {}) }),
    }),

  // --- Meridian: wishlist ---
  getWishlistItems: (personId?: number): Promise<MeridianWishlistItem[]> =>
    _fetch(`/meridian/wishlist/${personId ? `?person_id=${personId}` : ''}`),
  createWishlistItem: (data: {
    person_id: number; name: string; point_cost: number; description?: string
  }): Promise<MeridianWishlistItem> =>
    _fetch('/meridian/wishlist/', { method: 'POST', body: JSON.stringify(data) }),
  deleteWishlistItem: (id: number): Promise<void> =>
    _fetch(`/meridian/wishlist/${id}/`, { method: 'DELETE' }),
  contributeToWishlist: (id: number, amount: number, personId?: number): Promise<MeridianWishlistItem> =>
    _fetch(`/meridian/wishlist/${id}/contribute/`, {
      method: 'POST', body: JSON.stringify({ amount, ...(personId ? { person_id: personId } : {}) }),
    }),
  fulfillWishlistItem: (id: number): Promise<MeridianWishlistItem> =>
    _fetch(`/meridian/wishlist/${id}/fulfill/`, { method: 'POST' }),
  getWishlistRequests: (status?: string): Promise<MeridianWishlistRequest[]> =>
    _fetch(`/meridian/wishlist-requests/${status ? `?status=${status}` : ''}`),
  requestWishlistItem: (data: { requested_name: string; requested_description?: string; person_id?: number }): Promise<MeridianWishlistRequest> =>
    _fetch('/meridian/wishlist-requests/', { method: 'POST', body: JSON.stringify(data) }),
  approveWishlistRequest: (id: number, pointCost: number): Promise<MeridianWishlistItem> =>
    _fetch(`/meridian/wishlist-requests/${id}/approve/`, { method: 'POST', body: JSON.stringify({ point_cost: pointCost }) }),
  rejectWishlistRequest: (id: number, reason?: string): Promise<MeridianWishlistRequest> =>
    _fetch(`/meridian/wishlist-requests/${id}/reject/`, { method: 'POST', body: JSON.stringify({ reason }) }),

  // --- Meridian: settings + reports ---
  getMeridianSettings: (): Promise<MeridianSettings> => _fetch('/meridian/settings/'),
  updateMeridianSettings: (data: Partial<MeridianSettings>): Promise<MeridianSettings> =>
    _fetch('/meridian/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  getMeridianReports: (): Promise<MeridianReports> => _fetch('/meridian/reports/'),

  // --- Meridian: kiosk ---
  kioskMeridian: (): Promise<KioskMeridian> => _fetch('/kiosk/meridian/'),

  // --- Achievements ---
  getBadges: (): Promise<Badge[]> => _fetch('/achievements/badges/'),
  getMyBadges: (personId?: number): Promise<PersonBadge[]> =>
    _fetch(`/achievements/my-badges/${personId ? `?person_id=${personId}` : ''}`),

  // --- Notifications ---
  getNotifications: (unreadOnly?: boolean): Promise<NotificationList> =>
    _fetch(`/notifications/${unreadOnly ? '?unread=1' : ''}`),
  markNotificationRead: (id: number): Promise<unknown> =>
    _fetch(`/notifications/${id}/read/`, { method: 'POST' }),
  markAllNotificationsRead: (): Promise<unknown> =>
    _fetch('/notifications/read-all/', { method: 'POST' }),
}
