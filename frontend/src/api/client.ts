import type {
  AtlasList, AtlasListItem, AtlasNote, AtlasReminder,
  AuthUser, CalendarEvent, CalendarEventWrite, HubResponse, HubWidgetConfig, KioskUser,
  KioskMeridian, MeridianPointsResponse, MeridianReward,
  MeridianRewardRequest, MeridianTask, MeridianTaskCompletion,
  MeridianCategory, MeridianRoutine, MeridianGoal,
  MeridianWishlistItem, MeridianWishlistRequest, MeridianSettings,
  MeridianReports, MeridianAllowanceRow, Badge, PersonBadge, NotificationList, Person, AdminUser,
  AtlasSearchResults,
  EducationInstitution, EducationCourse, EducationAssessment, EducationClassSession,
  AssessmentNote, AssessmentFile, AcademicProfile, AcademicProfileResponse,
  NodeInfo, Household,
} from './types'

type CourseWrite = Partial<{
  name: string; code: string; institution_id: number | null; student_id: number | null
  teacher: string; start_date: string | null; end_date: string | null; colour: string
  description: string; is_archived: boolean; is_completed: boolean; credit_value: number; visibility: string
}>

type AssessmentWrite = Partial<{
  title: string; assessment_type: string; course_id: number | null
  assigned_to_person_id: number | null; due_at: string | null; is_all_day: boolean; status: string
  priority: string; weight: string; description: string; visibility: string
}>

type ClassSessionWrite = Partial<{
  title: string; course_id: number | null; student_id: number | null; location: string
  start_at: string; end_at: string | null; recurrence_rule: string; visibility: string
}>

type InstitutionWrite = Partial<{
  name: string; institution_type: string; location: string; notes: string; visibility: string
}>

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

// Like _fetch but lets the browser set Content-Type (needed for FormData multipart uploads).
async function _fetchRaw<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase()
  const csrfHeader: Record<string, string> = {}
  if (!SAFE_METHODS.has(method)) {
    const token = getCookie('csrftoken')
    if (token) csrfHeader['X-CSRFToken'] = token
  }
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { ...csrfHeader, ...init?.headers },
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
  patchMe: (data: Partial<{ display_name: string; colour: string; avatar: string; pin: string; password: string }>): Promise<AuthUser> =>
    _fetch('/auth/me/', { method: 'PATCH', body: JSON.stringify(data) }),
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
  createReminder: (data: { title: string; due_at?: string | null; is_all_day?: boolean; body?: string }): Promise<AtlasReminder> =>
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
  getMeridianAllowances: (): Promise<{ results: MeridianAllowanceRow[] }> =>
    _fetch('/meridian/allowances/'),
  updateMeridianAllowances: (results: MeridianAllowanceRow[]): Promise<{ results: MeridianAllowanceRow[] }> =>
    _fetch('/meridian/allowances/', { method: 'PATCH', body: JSON.stringify({ results }) }),
  getMeridianReports: (): Promise<MeridianReports> => _fetch('/meridian/reports/'),

  // --- Meridian: kiosk ---
  kioskMeridian: (): Promise<KioskMeridian> => _fetch('/kiosk/meridian/'),

  // --- Achievements ---
  getBadges: (): Promise<Badge[]> => _fetch('/achievements/badges/'),
  getMyBadges: (personId?: number): Promise<PersonBadge[]> =>
    _fetch(`/achievements/my-badges/${personId ? `?person_id=${personId}` : ''}`),

  // --- Education ---
  getInstitutions: (): Promise<EducationInstitution[]> => _fetch('/education/institutions/'),
  createInstitution: (data: InstitutionWrite): Promise<EducationInstitution> =>
    _fetch('/education/institutions/', { method: 'POST', body: JSON.stringify(data) }),
  updateInstitution: (id: number, data: InstitutionWrite): Promise<EducationInstitution> =>
    _fetch(`/education/institutions/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteInstitution: (id: number): Promise<void> =>
    _fetch(`/education/institutions/${id}/`, { method: 'DELETE' }),

  getCourses: (includeArchived = false): Promise<EducationCourse[]> =>
    _fetch(`/education/courses/${includeArchived ? '?archived=1' : ''}`),
  createCourse: (data: CourseWrite): Promise<EducationCourse> =>
    _fetch('/education/courses/', { method: 'POST', body: JSON.stringify(data) }),
  updateCourse: (id: number, data: CourseWrite): Promise<EducationCourse> =>
    _fetch(`/education/courses/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCourse: (id: number): Promise<void> =>
    _fetch(`/education/courses/${id}/`, { method: 'DELETE' }),

  getAssessments: (params?: { open?: boolean; course?: number }): Promise<EducationAssessment[]> => {
    const q = new URLSearchParams()
    if (params?.open) q.set('open', '1')
    if (params?.course) q.set('course', String(params.course))
    const qs = q.toString()
    return _fetch(`/education/assessments/${qs ? `?${qs}` : ''}`)
  },
  createAssessment: (data: AssessmentWrite): Promise<EducationAssessment> =>
    _fetch('/education/assessments/', { method: 'POST', body: JSON.stringify(data) }),
  updateAssessment: (id: number, data: AssessmentWrite): Promise<EducationAssessment> =>
    _fetch(`/education/assessments/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAssessment: (id: number): Promise<void> =>
    _fetch(`/education/assessments/${id}/`, { method: 'DELETE' }),

  getAssessmentNotes: (assessmentId: number): Promise<AssessmentNote[]> =>
    _fetch(`/education/assessments/${assessmentId}/notes/`),
  createAssessmentNote: (assessmentId: number, body: string): Promise<AssessmentNote> =>
    _fetch(`/education/assessments/${assessmentId}/notes/`, { method: 'POST', body: JSON.stringify({ body }) }),
  updateAssessmentNote: (assessmentId: number, noteId: number, body: string): Promise<AssessmentNote> =>
    _fetch(`/education/assessments/${assessmentId}/notes/${noteId}/`, { method: 'PATCH', body: JSON.stringify({ body }) }),
  deleteAssessmentNote: (assessmentId: number, noteId: number): Promise<void> =>
    _fetch(`/education/assessments/${assessmentId}/notes/${noteId}/`, { method: 'DELETE' }),

  getAssessmentFiles: (assessmentId: number): Promise<AssessmentFile[]> =>
    _fetch(`/education/assessments/${assessmentId}/files/`),
  uploadAssessmentFile: (assessmentId: number, file: File, label?: string): Promise<AssessmentFile> => {
    const fd = new FormData()
    fd.append('file', file)
    if (label) fd.append('label', label)
    return _fetchRaw(`/education/assessments/${assessmentId}/files/`, { method: 'POST', body: fd })
  },
  deleteAssessmentFile: (assessmentId: number, fileId: number): Promise<void> =>
    _fetch(`/education/assessments/${assessmentId}/files/${fileId}/`, { method: 'DELETE' }),

  getAcademicProfile: (personId: number): Promise<AcademicProfileResponse> =>
    _fetch(`/education/profile/${personId}/`),
  updateAcademicProfile: (personId: number, data: Partial<{
    institution_id: number | null; programme_name: string; credits_required: number;
    credits_per_course_default: number; graduation_year: number | null; notes: string;
  }>): Promise<AcademicProfile> =>
    _fetch(`/education/profile/${personId}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // --- Nodes (stacks) ---
  getNodes: (): Promise<NodeInfo[]> => _fetch('/nodes/'),
  enableNode: (key: string): Promise<NodeInfo> => _fetch(`/nodes/${key}/enable/`, { method: 'POST' }),
  disableNode: (key: string): Promise<NodeInfo> => _fetch(`/nodes/${key}/disable/`, { method: 'POST' }),

  // --- Household ---
  getHousehold: (): Promise<Household> => _fetch('/household/'),
  updateHousehold: (data: Partial<{ name: string; family_colour: string; timezone: string }>): Promise<Household> =>
    _fetch('/household/', { method: 'PATCH', body: JSON.stringify(data) }),

  getClassSessions: (params?: { course?: number }): Promise<EducationClassSession[]> =>
    _fetch(`/education/classes/${params?.course ? `?course=${params.course}` : ''}`),
  createClassSession: (data: ClassSessionWrite): Promise<EducationClassSession> =>
    _fetch('/education/classes/', { method: 'POST', body: JSON.stringify(data) }),
  updateClassSession: (id: number, data: ClassSessionWrite): Promise<EducationClassSession> =>
    _fetch(`/education/classes/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteClassSession: (id: number): Promise<void> =>
    _fetch(`/education/classes/${id}/`, { method: 'DELETE' }),

  // --- Notifications ---
  getNotifications: (unreadOnly?: boolean): Promise<NotificationList> =>
    _fetch(`/notifications/${unreadOnly ? '?unread=1' : ''}`),
  markNotificationRead: (id: number): Promise<unknown> =>
    _fetch(`/notifications/${id}/read/`, { method: 'POST' }),
  markAllNotificationsRead: (): Promise<unknown> =>
    _fetch('/notifications/read-all/', { method: 'POST' }),
}
