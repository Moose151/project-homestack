import type {
  AcademicProfile, AcademicProfileResponse, AdminUser, Appliance, AssessmentFile,
  AssessmentNote, AtlasList, AtlasListItem, AtlasListSuggestion, AtlasNote, AtlasReminder, AtlasSearchResults,
  Backup, ClassRepeat,
  Attachment, AttachmentSensitivity, AttachmentVisibility, AuthUser, Badge, Book, BookClub, BookLinkPreview,
  BookRating, BookShelfStatus, BooksUser, CalendarEvent, CalendarEventWrite, ClubBookEntry,
  ClubQueueItem, CornerResponse, EducationAssessment, EducationClassSession, EducationCourse, EducationEvent,
  EducationInstitution, FitnessExercise, FitnessProgram, FitnessRecord, FitnessSession,
  FitnessSessionExercise, FitnessSessionSet, GlobalSearchResponse, GuideDismissal, HomesteadSearchResults,
  Household, HouseholdCost, HouseholdPushDeviceGroup, HubResponse, HubWidgetConfig, Improvement, InsurancePolicy,
  KioskMeridian, KioskUser, LinkPreview, LinkWatch, MaintenanceTask, MeridianAllowanceRow, MeridianCategory,
  MeridianGoal, MeridianPointsResponse, MeridianReports, MeridianReward, MeridianRewardRequest,
  MeridianRoutine, MeridianSettings, MeridianTask, MeridianTaskCompletion,
  MeridianWishlistItem, MeridianWishlistRequest, NodeInfo, NotificationList, NotificationPreference,
  Person, PushDevice,
  PersonBadge, PersonalBookEntry, Pet, PetAppointment, PetTreatment, Pool, PoolStatus,
  PoolWrite, Property, RoomArea, RoomAreaType, RoomDetailResponse, RoomItemPriority,
  RoomItemStatus, RoomItemType, RoomListResponse, RoomPlanItem, RoomPlanMode, RoomPlanProduct,
  RotatingSchedule, RotatingScheduleOccurrence, RotatingScheduleWrite, ServiceProvider,
  SolaceAnnualSummary, SolaceBalanceForecast, SolaceBalanceSnapshot, SolaceBill,
  SolaceBillImportPreview, SolaceBillOccurrence, SolaceBillTimeline, SolaceBootstrap,
  SolaceBucket, SolaceBucketEntry, SolaceBucketEntryWrite, SolaceBucketPurpose, SolaceCategory,
  SolaceCategoryReport, SolaceChecklistItem, SolaceChecklistPreference, SolaceCloseoutResponse,
  SolaceCycleCloseout, SolaceCycleHistoryRow, SolaceHealth, SolaceIncomeAllocation,
  SolaceIncomeAllocationWrite, SolaceNow, SolacePayCyclePlan, SolacePayday, SolacePurchase,
  SolaceSchedule, SolaceSearchResults, SolaceSettings, UserNotificationSettings, UtilityBill,
  UtilityBillWrite, UtilityType, UtilityUsageResponse, WaterTest,
  WaterTestWrite, WikiCategory, WikiPage
} from './types'

/** Which screen is signing in. Only 'web' earns the longer re-authentication window. */
export type LoginSurface = 'web' | 'kiosk'

type CourseWrite = Partial<{
  name: string; code: string; institution_id: number | null; student_id: number | null
  teacher: string; start_date: string | null; end_date: string | null; colour: string
  description: string; is_archived: boolean; is_completed: boolean; credit_value: number; visibility: string
}>

type AssessmentWrite = Partial<{
  title: string; assessment_type: string; course_id: number | null
  assigned_to_person_ids: number[]; due_at: string | null; is_all_day: boolean; status: string
  priority: string; weight: string; description: string; visibility: string
}>

type ClassSessionWrite = Partial<{
  title: string; course_id: number | null; student_id: number | null; location: string
  start_at: string; end_at: string | null; recurrence_rule: string; visibility: string
  /** Friendlier than end_at when adding a class; the server turns it into end_at. */
  duration_minutes: number
  /** With repeat_until, creates one class per occurrence instead of a single row. */
  repeat: ClassRepeat | ''
  repeat_until: string | null
}>

type EventWrite = Partial<{
  title: string; event_type: string; course_id: number | null; institution_id: number | null
  assigned_to_person_ids: number[]; start_at: string; end_at: string | null
  is_all_day: boolean; location: string; description: string; recurrence_rule: string
  visibility: string
}>

type WikiCategoryWrite = Partial<{
  name: string; colour: string; icon: string; display_order: number; is_hidden: boolean
}>

type WikiPageWrite = Partial<{
  title: string; body: string; category_id: number | null; tags: string
  is_favourite: boolean; is_emergency: boolean; is_kiosk_safe: boolean
  visibility: string; sensitivity: string
}>

type PetWrite = Partial<{
  name: string; species: string; breed: string; avatar: string; colour: string
  date_of_birth: string | null; adoption_date: string | null; notes: string
  vet_name: string; vet_phone: string; microchip_number: string
  insurance_provider: string; insurance_policy_number: string; food_notes: string
  is_archived: boolean; visibility: string
}>

type TreatmentWrite = Partial<{
  pet_id: number; treatment_type: string; name: string
  last_done_at: string | null; next_due_at: string | null
  recurrence_rule: string; notes: string; visibility: string
}>

type AppointmentWrite = Partial<{
  pet_id: number; title: string; provider: string; location: string
  start_at: string; end_at: string | null; notes: string; visibility: string
}>

export type FitnessProgramWrite = Partial<{
  name: string; description: string; visibility: 'private' | 'household'; is_archived: boolean
  person_ids: number[]
  workouts: Array<{
    name: string; position: number; notes?: string
    exercises: Array<{
      exercise_id: number; position: number; target_sets: number; target_reps?: number | null
      target_weight?: string | null; target_duration_seconds?: number | null
      target_distance?: string | null; rest_seconds?: number | null; notes?: string
    }>
  }>
}>

type PropertyWrite = Partial<{
  name: string; address: string; property_type: string; tenure: string
  purchase_date: string | null; move_in_date: string | null; year_built: string
  is_primary: boolean; notes: string; water_shutoff: string; gas_shutoff: string
  electricity_consumer_unit: string; boiler_location: string; visibility: string
}>

type ProviderWrite = Partial<{
  name: string; trade: string; company: string; phone: string; email: string
  website: string; last_used_at: string | null; notes: string; visibility: string
}>

type ApplianceWrite = Partial<{
  name: string; category: string; brand: string; model_number: string; serial_number: string
  room: string; purchase_date: string | null; warranty_expires_at: string | null
  warranty_provider: string; manual_url: string; notes: string; visibility: string
}>

type MaintenanceWrite = Partial<{
  appliance_id: number | null; provider_id: number | null; assigned_to_person_ids: number[]
  title: string; category: string; next_due_at: string | null; is_all_day: boolean
  recurrence_rule: string; notes: string; visibility: string
}>

type ImprovementWrite = Partial<{
  assigned_to_person_ids: number[]; title: string; description: string; status: string
  priority: string; room: string; target_date: string | null; is_all_day: boolean
  project_ref: number | null; notes: string; visibility: string
}>

type InsurancePolicyWrite = Partial<{
  name: string; policy_type: string; provider: string; policy_number: string
  premium_amount: string; billing_cycle: string; next_renewal_at: string | null
  recurrence_rule: string; standard_excess: string; additional_excesses: string
  coverage_summary: string; contact_phone: string; portal_url: string
  is_active: boolean; notes: string; visibility: string
}>

type HouseholdCostWrite = Partial<{
  name: string; cost_type: string; provider: string; account_number: string
  amount: string; billing_cycle: string; next_due_at: string | null
  recurrence_rule: string; is_active: boolean; notes: string; visibility: string
}>

type RoomWrite = Partial<{
  name: string; area_type: RoomAreaType; description: string; icon: string; colour: string
  display_order: number; floorplan_data: Record<string, unknown>; visibility: string
}>

type RoomItemWrite = Partial<{
  assigned_to_person_ids: number[]; title: string; plan_mode: RoomPlanMode; item_type: RoomItemType
  status: RoomItemStatus; priority: RoomItemPriority; description: string
  quantity: string; estimated_unit_cost: string; actual_cost: string | null
  notes: string; position: number; visibility: string
}>

type RoomProductWrite = Partial<{
  title: string; url: string; image_url: string; source_image_url: string; retailer: string; currency: string
  quantity: string; unit_cost: string; is_chosen: boolean; is_purchased: boolean
  actual_cost: string | null; notes: string; position: number; cache_image: boolean; price_watch_enabled: boolean
}>

type SolaceBillWrite = Partial<{
  name: string; category: string; provider: string; amount: string
  due_at: string | null; is_all_day: boolean; recurrence_rule: string
  end_date: string | null; is_active: boolean; is_autopay: boolean
  include_in_set_aside: boolean
  home_destination: '' | 'insurance_policy' | 'household_cost' | 'maintenance'
  occurrence_update_scope: 'future_unpaid' | 'all_unpaid'
  is_paid: boolean; paid_at: string | null; notes: string; visibility: string; sensitivity: string
}>

type SolacePaydayWrite = Partial<{
  title: string; owner_name: string
  income_scope: SolacePayday['income_scope']; allocation_mode: SolacePayday['allocation_mode']
  lump_bucket_id: number | null
  expected_amount: string; pay_at: string | null; is_all_day: boolean
  recurrence_rule: string; received_at: string | null; is_active: boolean
  notes: string; visibility: string; sensitivity: string
}>

type SolacePurchaseWrite = Partial<{
  name: string; category: string; target_amount: string; saved_amount: string
  target_date: string | null; is_all_day: boolean; status: string; priority: string
  notes: string; visibility: string; sensitivity: string
}>

type SolaceBucketWrite = Partial<{
  purpose: SolaceBucketPurpose
  name: string; category: string; target_amount: string; current_amount: string
  allocation_method: 'percentage' | 'fixed'; allocation_value: string
  rounding_increment: string; cap_to_remaining: boolean; is_active: boolean; position: number
  notes: string; visibility: string; sensitivity: string
}>

type SolaceChecklistWrite = Partial<{
  title: string; bucket_id: number | null; bill_id: number | null; amount_hint: string
  position: number; is_complete: boolean; notes: string; visibility: string; sensitivity: string
}>

type SolaceSettingsWrite = Partial<{
  currency_symbol: string; budget_year: number | null; cycle_anchor_date: string | null
  default_buffer_amount: string
  payday_bill_handling: 'new_cycle' | 'previous_cycle'; show_help_tips: boolean
  dashboard_reminders: boolean; due_soon_days: number
}>

type SolaceCategoryWrite = Partial<{
  name: string; category_type: 'bill' | 'purchase' | 'both'
  is_active: boolean; position: number; visibility: string; sensitivity: string
}>

type SolaceBalanceWrite = Partial<{
  snapshot_date: string; balance: string; notes: string; visibility: string; sensitivity: string
}>

type InstitutionWrite = Partial<{
  name: string; institution_type: string; location: string; notes: string; visibility: string
}>

type ItemWrite = Partial<{
  title: string; notes: string; quantity: string; priority: string; position: number
  due_at: string | null; assigned_to_person_ids: number[]
  product_url: string; source_image_url: string; retailer: string; unit_price: string | null
  currency: string; cache_image: boolean; price_watch_enabled: boolean
}>

type UserWrite = Partial<{
  username: string; display_name: string; role: string; email: string; colour: string
  avatar: string; is_child_account: boolean; is_active: boolean; pin: string; password: string
  link_person_id: number | null; create_person: boolean; solace_access: boolean
}>

type BookWrite = Partial<{
  title: string; author: string; pages: number | null; genre: string; isbn: string
  publication_date: string; description: string; cover_url: string; source_url: string
}>

type ShelfWrite = Partial<{
  book_id: number; book: BookWrite; status: BookShelfStatus; position: number
}>

const BASE = '/api/v1'
export const AUTH_EXPIRED_EVENT = 'homestack:auth-expired'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, statusText: string, detail: string) {
    let readable = detail
    try {
      const parsed = JSON.parse(detail)
      readable = typeof parsed.detail === 'string'
        ? parsed.detail
        : Object.values(parsed).flat().join(' ')
    } catch {
      // Plain-text API errors are already readable.
    }
    super(readable || `${status} ${statusText}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

type CacheEntry = { expiresAt: number; value?: unknown; request?: Promise<unknown> }
const sharedGetCache = new Map<string, CacheEntry>()

function clearSharedCache(...paths: string[]) {
  paths.forEach(path => sharedGetCache.delete(path))
}

function cachedGet<T>(path: string, ttlMs = 30_000): Promise<T> {
  const now = Date.now()
  const cached = sharedGetCache.get(path)
  if (cached?.value !== undefined && cached.expiresAt > now) {
    return Promise.resolve(cached.value as T)
  }
  if (cached?.request && cached.expiresAt > now) {
    return cached.request as Promise<T>
  }
  const request = _fetch<T>(path)
    .then(value => {
      sharedGetCache.set(path, { value, expiresAt: Date.now() + ttlMs })
      return value
    })
    .catch(error => {
      sharedGetCache.delete(path)
      throw error
    })
  sharedGetCache.set(path, { request, expiresAt: now + ttlMs })
  return request
}

function readableErrorDetail(status: number, contentType: string | null, body: string): string {
  const text = body.trim()
  if (!text) {
    return status >= 500 ? 'HomeStack hit a server error. Try again.' : 'HomeStack could not complete that request.'
  }
  if (contentType?.includes('application/json')) {
    try {
      const parsed = JSON.parse(text) as unknown
      if (typeof parsed === 'string') return parsed
      if (parsed && typeof parsed === 'object') {
        const obj = parsed as Record<string, unknown>
        const detail = obj.detail ?? obj.error ?? obj.message ?? obj.non_field_errors
        if (Array.isArray(detail)) return detail.join(' ')
        if (typeof detail === 'string') return detail
      }
    } catch {
      return text
    }
  }
  if (status >= 500 && (contentType?.includes('text/html') || /^<!doctype html>|^<html[\s>]/i.test(text))) {
    console.error('HomeStack API server error response', { status, body: text })
    return 'HomeStack hit a server error. Try again.'
  }
  return text
}

function apiError(path: string, status: number, statusText: string, detail: string): ApiError {
  const isAuthEndpoint = path.startsWith('/auth/')
  const sessionExpired = (status === 401 || status === 403)
    && /not authenticated|authentication credentials were not provided/i.test(detail)
  if (!isAuthEndpoint && sessionExpired) {
    sharedGetCache.clear()
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }
  return new ApiError(status, statusText, detail)
}

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
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...csrfHeader, ...init?.headers },
      ...init,
    })
  } catch {
    throw new Error('HomeStack could not reach the server. Check your connection and try again.')
  }
  if (!res.ok) {
    const text = await res.text()
    throw apiError(path, res.status, res.statusText, readableErrorDetail(res.status, res.headers.get('Content-Type'), text))
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
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      headers: { ...csrfHeader, ...init?.headers },
      ...init,
    })
  } catch {
    throw new Error('HomeStack could not reach the server. Check your connection and try again.')
  }
  if (!res.ok) {
    const text = await res.text()
    throw apiError(path, res.status, res.statusText, readableErrorDetail(res.status, res.headers.get('Content-Type'), text))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
    // --- Auth ---
  getKioskUsers: (): Promise<KioskUser[]> => _fetch('/auth/kiosk-users/'),
  // `surface` decides how long password elevation lasts: the kiosk is a shared screen, so it
  // expires in a minute where the web gets five. A caller that says nothing is treated as the
  // kiosk, so the web must declare itself rather than rely on the default.
  pinLogin: (username: string, pin: string, surface: LoginSurface = 'web'): Promise<AuthUser> =>
    _fetch<AuthUser>('/auth/pin-login/', { method: 'POST', body: JSON.stringify({ username, pin, surface }) })
      .then(value => { sharedGetCache.clear(); return value }),
  passwordLogin: (username: string, password: string, surface: LoginSurface = 'web'): Promise<AuthUser> =>
    _fetch<AuthUser>('/auth/password-login/', { method: 'POST', body: JSON.stringify({ username, password, surface }) })
      .then(value => { sharedGetCache.clear(); return value }),
  logout: (): Promise<void> =>
    _fetch<void>('/auth/logout/', { method: 'POST' })
      .finally(() => sharedGetCache.clear()),
  me: (): Promise<AuthUser> => _fetch('/auth/me/'),
  patchMe: (data: Partial<{ display_name: string; colour: string; avatar: string; pin: string; password: string }>): Promise<AuthUser> =>
    _fetch('/auth/me/', { method: 'PATCH', body: JSON.stringify(data) }),
  reauth: (password: string): Promise<void> =>
    _fetch('/auth/reauth/', { method: 'POST', body: JSON.stringify({ password }) }),
  getGuideDismissals: (): Promise<GuideDismissal[]> => _fetch('/auth/guide-dismissals/'),
  dismissGuide: (guideIdentifier: string, guideVersion = '1'): Promise<GuideDismissal> =>
    _fetch('/auth/guide-dismissals/', {
      method: 'POST', body: JSON.stringify({ guide_identifier: guideIdentifier, guide_version: guideVersion }),
    }),
  resetGuideDismissals: (): Promise<{ removed: number }> =>
    _fetch('/auth/guide-dismissals/', { method: 'DELETE' }),
  globalSearch: (q: string): Promise<GlobalSearchResponse> =>
    _fetch(`/search/?q=${encodeURIComponent(q)}`),

  // --- People ---
  getPeople: (): Promise<Person[]> => cachedGet('/people/'),
  updatePerson: (id: number, data: Partial<Person>): Promise<Person> =>
    _fetch<Person>(`/people/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
      .then(value => { clearSharedCache('/people/'); return value }),

  // --- Household Corners ---
  getCorner: (personId: number, days = 30): Promise<CornerResponse> =>
    _fetch(`/corners/${personId}/?days=${days}`),
  toggleCornerReaction: (personId: number, activityKey: string, emoji: string): Promise<{ active: boolean; corner: CornerResponse }> =>
    _fetch(`/corners/${personId}/reactions/`, { method: 'POST', body: JSON.stringify({ activity_key: activityKey, emoji }) }),

  // --- Safe link previews and price watches ---
  previewProductLink: (url: string): Promise<LinkPreview> =>
    _fetch('/link-imports/preview/', { method: 'POST', body: JSON.stringify({ url, kind: 'product' }) }),
  previewBook: (query: string): Promise<BookLinkPreview> =>
    _fetch('/link-imports/preview/', { method: 'POST', body: JSON.stringify({ query, kind: 'book' }) }),
  getLinkWatches: (): Promise<LinkWatch[]> => _fetch('/link-imports/watches/'),
  updateLinkWatch: (id: number, data: Partial<Pick<LinkWatch, 'is_active' | 'rule' | 'threshold_percent' | 'target_price'>>): Promise<LinkWatch> =>
    _fetch(`/link-imports/watches/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // --- Shared attachments (permission-checked; storage paths are never public) ---
  getAttachments: (filters?: Partial<{
    linked_node: number; linked_record_type: string; linked_record_id: number
  }>): Promise<Attachment[]> => {
    const query = new URLSearchParams()
    if (filters?.linked_node) query.set('linked_node', String(filters.linked_node))
    if (filters?.linked_record_type) query.set('linked_record_type', filters.linked_record_type)
    if (filters?.linked_record_id) query.set('linked_record_id', String(filters.linked_record_id))
    return _fetch(`/attachments/${query.size ? `?${query}` : ''}`)
  },
  uploadAttachment: (file: File, metadata?: Partial<{
    linked_node: number; linked_record_type: string; linked_record_id: number
    visibility: AttachmentVisibility; sensitivity: AttachmentSensitivity
  }>): Promise<Attachment> => {
    const data = new FormData()
    data.append('file', file)
    if (metadata?.linked_node) data.append('linked_node', String(metadata.linked_node))
    if (metadata?.linked_record_type) data.append('linked_record_type', metadata.linked_record_type)
    if (metadata?.linked_record_id) data.append('linked_record_id', String(metadata.linked_record_id))
    if (metadata?.visibility) data.append('visibility', metadata.visibility)
    if (metadata?.sensitivity) data.append('sensitivity', metadata.sensitivity)
    return _fetchRaw('/attachments/', { method: 'POST', body: data })
  },
  attachmentDownloadUrl: (id: number): string => `${BASE}/attachments/${id}/download/`,
  deleteAttachment: (id: number): Promise<void> =>
    _fetch(`/attachments/${id}/`, { method: 'DELETE' }),

  // --- User management (admin) ---
  getUsers: (): Promise<AdminUser[]> => cachedGet('/users/', 15_000),
  createUser: (data: UserWrite): Promise<AdminUser> =>
    _fetch<AdminUser>('/users/', { method: 'POST', body: JSON.stringify(data) })
      .then(value => { clearSharedCache('/users/', '/people/'); return value }),
  updateUser: (id: number, data: UserWrite): Promise<AdminUser> =>
    _fetch<AdminUser>(`/users/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
      .then(value => { clearSharedCache('/users/', '/people/'); return value }),
  deactivateUser: (id: number): Promise<void> =>
    _fetch<void>(`/users/${id}/`, { method: 'DELETE' })
      .then(value => { clearSharedCache('/users/', '/people/'); return value }),

  // --- Hub ---
  hub: (): Promise<HubResponse> => _fetch('/hub/'),
  kioskHub: (): Promise<HubResponse> => _fetch('/hub/kiosk/'),
  getHubWidgetConfig: (): Promise<{ widgets: HubWidgetConfig[] }> => _fetch('/hub/widgets/'),
  setHouseholdWidget: (key: string, data: Partial<{ is_enabled: boolean; display_order: number; size: string; settings: { title: string; target_date: string; target_time?: string } }>):
    Promise<{ widgets: HubWidgetConfig[] }> =>
    _fetch(`/hub/widgets/${key}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  setUserWidget: (key: string, data: Partial<{ is_enabled: boolean; display_order: number }>):
    Promise<{ widgets: HubWidgetConfig[] }> =>
    _fetch(`/hub/widgets/${key}/me/`, { method: 'PATCH', body: JSON.stringify(data) }),
  setUserWidgetOrder: (keys: string[]): Promise<{ widgets: HubWidgetConfig[] }> =>
    _fetch('/hub/widgets/me/order/', { method: 'PATCH', body: JSON.stringify({ keys }) }),

  // --- Atlas lists ---
  getLists: (): Promise<AtlasList[]> => _fetch('/atlas/lists/'),
  getList: (id: number): Promise<AtlasList> => _fetch(`/atlas/lists/${id}/`),
  createList: (data: { title: string; list_type: string; visibility?: string; owner_person?: number | null }): Promise<AtlasList> =>
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
  getListSuggestions: (listId: number): Promise<AtlasListSuggestion[]> =>
    _fetch(`/atlas/lists/${listId}/suggestions/`),
  suggestListItem: (listId: number, data: ItemWrite): Promise<AtlasListSuggestion> =>
    _fetch(`/atlas/lists/${listId}/suggestions/`, { method: 'POST', body: JSON.stringify(data) }),
  reviewListSuggestion: (listId: number, suggestionId: number, action: 'accept' | 'dismiss'): Promise<AtlasListSuggestion> =>
    _fetch(`/atlas/lists/${listId}/suggestions/${suggestionId}/${action}/`, { method: 'POST' }),

  // --- Atlas search ---
  searchAtlas: (q: string): Promise<AtlasSearchResults> =>
    _fetch(`/atlas/search/?q=${encodeURIComponent(q)}`),

  // --- Atlas notes ---
  getNotes: (): Promise<AtlasNote[]> => _fetch('/atlas/notes/'),
  createNote: (data: { title: string; body?: string; visibility?: string }): Promise<AtlasNote> =>
    _fetch('/atlas/notes/', { method: 'POST', body: JSON.stringify(data) }),
  updateNote: (id: number, data: Partial<{ title: string; body: string; visibility: string }>): Promise<AtlasNote> =>
    _fetch(`/atlas/notes/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteNote: (id: number): Promise<void> => _fetch(`/atlas/notes/${id}/`, { method: 'DELETE' }),

  // --- Atlas reminders ---
  getReminders: (upcoming?: boolean): Promise<AtlasReminder[]> =>
    _fetch(`/atlas/reminders/${upcoming ? '?upcoming=1' : ''}`),
  createReminder: (data: { title: string; due_at?: string | null; is_all_day?: boolean; body?: string; assigned_to_person_ids?: number[]; notifications_enabled?: boolean }): Promise<AtlasReminder> =>
    _fetch('/atlas/reminders/', { method: 'POST', body: JSON.stringify(data) }),
  updateReminder: (id: number, data: Partial<{ title: string; due_at: string | null; is_all_day: boolean; body: string; assigned_to_person_ids: number[]; notifications_enabled: boolean }>): Promise<AtlasReminder> =>
    _fetch(`/atlas/reminders/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteReminder: (id: number): Promise<void> => _fetch(`/atlas/reminders/${id}/`, { method: 'DELETE' }),

  // --- Calendar ---
  getEvents: (params?: { start?: string; end?: string; node?: string; person?: number; upcoming?: boolean; agenda?: boolean }): Promise<CalendarEvent[]> => {
    const q = new URLSearchParams()
    if (params?.start) q.set('start', params.start)
    if (params?.end) q.set('end', params.end)
    if (params?.node) q.set('node', params.node)
    if (params?.person) q.set('person', String(params.person))
    if (params?.upcoming) q.set('upcoming', '1')
    if (params?.agenda) q.set('agenda', '1')
    const s = q.toString()
    return _fetch(`/calendar/events/${s ? `?${s}` : ''}`)
  },
  getAtlasContacts: (): Promise<import('./types').AtlasContact[]> => _fetch('/atlas/contacts/'),
  createAtlasContact: (data: Partial<import('./types').AtlasContact>): Promise<import('./types').AtlasContact> =>
    _fetch('/atlas/contacts/', { method: 'POST', body: JSON.stringify(data) }),
  updateAtlasContact: (id: number, data: Partial<import('./types').AtlasContact>): Promise<import('./types').AtlasContact> =>
    _fetch(`/atlas/contacts/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAtlasContact: (id: number): Promise<void> => _fetch(`/atlas/contacts/${id}/`, { method: 'DELETE' }),
  getBirthdayOccurrences: (start: string, end: string): Promise<import('./types').BirthdayOccurrence[]> =>
    _fetch(`/atlas/birthday-occurrences/?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),

  // --- Travel ---
  getTrips: (): Promise<import('./types').Trip[]> => _fetch('/travel/trips/'),
  getTrip: (id: number): Promise<import('./types').Trip> => _fetch(`/travel/trips/${id}/`),
  createTrip: (data: Record<string, unknown>): Promise<import('./types').Trip> => _fetch('/travel/trips/', { method: 'POST', body: JSON.stringify(data) }),
  updateTrip: (id: number, data: Record<string, unknown>): Promise<import('./types').Trip> => _fetch(`/travel/trips/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTrip: (id: number): Promise<void> => _fetch(`/travel/trips/${id}/`, { method: 'DELETE' }),
  createTravelBooking: (tripId: number, data: Record<string, unknown>): Promise<import('./types').TravelBooking> => _fetch(`/travel/trips/${tripId}/bookings/`, { method: 'POST', body: JSON.stringify(data) }),
  updateTravelBooking: (id: number, data: Record<string, unknown>): Promise<import('./types').TravelBooking> => _fetch(`/travel/bookings/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTravelBooking: (id: number): Promise<void> => _fetch(`/travel/bookings/${id}/`, { method: 'DELETE' }),
  createItineraryItem: (tripId: number, data: Record<string, unknown>): Promise<import('./types').TravelItineraryItem> => _fetch(`/travel/trips/${tripId}/itinerary/`, { method: 'POST', body: JSON.stringify(data) }),
  updateItineraryItem: (id: number, data: Record<string, unknown>): Promise<import('./types').TravelItineraryItem> => _fetch(`/travel/itinerary/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteItineraryItem: (id: number): Promise<void> => _fetch(`/travel/itinerary/${id}/`, { method: 'DELETE' }),
  getTravelIdeas: (): Promise<import('./types').TravelIdea[]> => _fetch('/travel/ideas/'),
  createTravelIdea: (data: Record<string, unknown>): Promise<import('./types').TravelIdea> => _fetch('/travel/ideas/', { method: 'POST', body: JSON.stringify(data) }),
  updateTravelIdea: (id: number, data: Record<string, unknown>): Promise<import('./types').TravelIdea> => _fetch(`/travel/ideas/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTravelIdea: (id: number): Promise<void> => _fetch(`/travel/ideas/${id}/`, { method: 'DELETE' }),
  convertTravelIdea: (id: number): Promise<import('./types').Trip> => _fetch(`/travel/ideas/${id}/convert/`, { method: 'POST' }),
  createEvent: (data: CalendarEventWrite): Promise<CalendarEvent> =>
    _fetch('/calendar/events/', { method: 'POST', body: JSON.stringify(data) }),
  updateEvent: (id: number, data: Partial<CalendarEventWrite>): Promise<CalendarEvent> =>
    _fetch(`/calendar/events/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteEvent: (id: number): Promise<void> =>
    _fetch(`/calendar/events/${id}/`, { method: 'DELETE' }),
  getRotatingSchedules: (): Promise<RotatingSchedule[]> =>
    _fetch('/calendar/rotations/'),
  createRotatingSchedule: (data: RotatingScheduleWrite): Promise<RotatingSchedule> =>
    _fetch('/calendar/rotations/', { method: 'POST', body: JSON.stringify(data) }),
  updateRotatingSchedule: (id: number, data: Partial<RotatingScheduleWrite>): Promise<RotatingSchedule> =>
    _fetch(`/calendar/rotations/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRotatingSchedule: (id: number): Promise<void> =>
    _fetch(`/calendar/rotations/${id}/`, { method: 'DELETE' }),
  getRotatingScheduleOccurrences: (start: string, end: string): Promise<RotatingScheduleOccurrence[]> => {
    const q = new URLSearchParams({ start, end })
    return _fetch(`/calendar/rotation-occurrences/?${q}`)
  },
  setRotatingScheduleException: (
    scheduleId: number, date: string, data: { state: 'primary' | 'secondary'; note?: string },
  ): Promise<void> =>
    _fetch(`/calendar/rotations/${scheduleId}/exceptions/${date}/`, {
      method: 'PUT', body: JSON.stringify(data),
    }),
  deleteRotatingScheduleException: (scheduleId: number, date: string): Promise<void> =>
    _fetch(`/calendar/rotations/${scheduleId}/exceptions/${date}/`, { method: 'DELETE' }),

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
    assigned_to_person_ids?: number[]; is_hot?: boolean; due_at?: string
    hot_bonus_points?: number; hot_label?: string; category_id?: number | null
    completion_behavior?: string; completion_scope?: string; availability_window?: string
    recurrence_rule?: string
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
    assigned_to_person_ids: number[]; is_hot: boolean; hot_bonus_points: number
    hot_label: string; completion_behavior: string; due_at: string | null
    completion_scope: string; recurrence_rule: string; visibility: string
    is_active: boolean; is_archived: boolean
  }>): Promise<MeridianTask> =>
    _fetch(`/meridian/tasks/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // --- Meridian: routines ---
  getMeridianRoutines: (personId?: number): Promise<MeridianRoutine[]> =>
    _fetch(`/meridian/routines/${personId ? `?person_id=${personId}` : ''}`),
  createMeridianRoutine: (data: {
    title: string; points: number; description?: string; assigned_to_person_ids?: number[]
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
  searchEducation: (q: string): Promise<{ courses: EducationCourse[]; assessments: EducationAssessment[]; class_sessions: EducationClassSession[]; events: EducationEvent[] }> =>
    _fetch(`/education/search/?q=${encodeURIComponent(q)}`),
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
  getNodes: (): Promise<NodeInfo[]> => cachedGet('/nodes/', 30_000),
  enableNode: (key: string): Promise<NodeInfo> =>
    _fetch<NodeInfo>(`/nodes/${key}/enable/`, { method: 'POST' })
      .then(value => { clearSharedCache('/nodes/'); return value }),
  disableNode: (key: string): Promise<NodeInfo> =>
    _fetch<NodeInfo>(`/nodes/${key}/disable/`, { method: 'POST' })
      .then(value => { clearSharedCache('/nodes/'); return value }),
  updateNodeConfiguration: (key: string, data: {
    requires_reauthentication: boolean
  }): Promise<NodeInfo> =>
    _fetch<NodeInfo>(`/nodes/${key}/configuration/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }).then(value => { clearSharedCache('/nodes/'); return value }),

  // --- Household ---
  getHousehold: (): Promise<Household> => cachedGet('/household/', 30_000),
  updateHousehold: (data: Partial<{ name: string; family_colour: string; timezone: string; calendar_default_view: string; calendar_week_start: number; calendar_time_format: string }>): Promise<Household> =>
    _fetch<Household>('/household/', { method: 'PATCH', body: JSON.stringify(data) })
      .then(value => { clearSharedCache('/household/'); return value }),

  getClassSessions: (params?: { course?: number }): Promise<EducationClassSession[]> =>
    _fetch(`/education/classes/${params?.course ? `?course=${params.course}` : ''}`),
  /** Returns every class created — one for a single class, several for a repeating series. */
  createClassSession: (data: ClassSessionWrite): Promise<EducationClassSession[]> =>
    _fetch('/education/classes/', { method: 'POST', body: JSON.stringify(data) }),
  updateClassSession: (id: number, data: ClassSessionWrite): Promise<EducationClassSession> =>
    _fetch(`/education/classes/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteClassSession: (id: number): Promise<void> =>
    _fetch(`/education/classes/${id}/`, { method: 'DELETE' }),
  /** Removes every remaining class sharing this one's series_key. */
  deleteClassSeries: (id: number): Promise<{ deleted: number }> =>
    _fetch(`/education/classes/${id}/?series=1`, { method: 'DELETE' }),

  getBackups: (): Promise<Backup[]> => _fetch('/backups/'),
  /** Runs synchronously and needs recent password re-authentication. */
  createBackup: (): Promise<Backup> => _fetch('/backups/', { method: 'POST' }),

  getEducationEvents: (params?: { upcoming?: boolean; course?: number }): Promise<EducationEvent[]> => {
    const q = new URLSearchParams()
    if (params?.upcoming) q.set('upcoming', '1')
    if (params?.course) q.set('course', String(params.course))
    const qs = q.toString()
    return _fetch(`/education/events/${qs ? `?${qs}` : ''}`)
  },
  createEducationEvent: (data: EventWrite): Promise<EducationEvent> =>
    _fetch('/education/events/', { method: 'POST', body: JSON.stringify(data) }),
  updateEducationEvent: (id: number, data: EventWrite): Promise<EducationEvent> =>
    _fetch(`/education/events/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteEducationEvent: (id: number): Promise<void> =>
    _fetch(`/education/events/${id}/`, { method: 'DELETE' }),

  // --- Home Wiki ---
  searchWiki: (q: string): Promise<{ pages: WikiPage[] }> =>
    _fetch(`/wiki/search/?q=${encodeURIComponent(q)}`),
  getWikiCategories: (includeHidden = false): Promise<WikiCategory[]> =>
    _fetch(`/wiki/categories/${includeHidden ? '?hidden=1' : ''}`),
  createWikiCategory: (data: WikiCategoryWrite): Promise<WikiCategory> =>
    _fetch('/wiki/categories/', { method: 'POST', body: JSON.stringify(data) }),
  updateWikiCategory: (id: number, data: WikiCategoryWrite): Promise<WikiCategory> =>
    _fetch(`/wiki/categories/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteWikiCategory: (id: number): Promise<void> =>
    _fetch(`/wiki/categories/${id}/`, { method: 'DELETE' }),
  getWikiPages: (params?: { category?: number; favourites?: boolean; emergency?: boolean; recent?: boolean }): Promise<WikiPage[]> => {
    const q = new URLSearchParams()
    if (params?.category) q.set('category', String(params.category))
    if (params?.favourites) q.set('favourites', '1')
    if (params?.emergency) q.set('emergency', '1')
    if (params?.recent) q.set('recent', '1')
    const qs = q.toString()
    return _fetch(`/wiki/pages/${qs ? `?${qs}` : ''}`)
  },
  createWikiPage: (data: WikiPageWrite): Promise<WikiPage> =>
    _fetch('/wiki/pages/', { method: 'POST', body: JSON.stringify(data) }),
  updateWikiPage: (id: number, data: WikiPageWrite): Promise<WikiPage> =>
    _fetch(`/wiki/pages/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteWikiPage: (id: number): Promise<void> =>
    _fetch(`/wiki/pages/${id}/`, { method: 'DELETE' }),

  // --- Pets ---
  searchPets: (q: string): Promise<{ pets: Pet[]; treatments: PetTreatment[]; appointments: PetAppointment[] }> =>
    _fetch(`/pets/search/?q=${encodeURIComponent(q)}`),
  getPets: (includeArchived = false): Promise<Pet[]> =>
    _fetch(`/pets/pets/${includeArchived ? '?archived=1' : ''}`),
  createPet: (data: PetWrite): Promise<Pet> =>
    _fetch('/pets/pets/', { method: 'POST', body: JSON.stringify(data) }),
  updatePet: (id: number, data: PetWrite): Promise<Pet> =>
    _fetch(`/pets/pets/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePet: (id: number): Promise<void> =>
    _fetch(`/pets/pets/${id}/`, { method: 'DELETE' }),

  getPetTreatments: (params?: { pet?: number; due?: boolean }): Promise<PetTreatment[]> => {
    const q = new URLSearchParams()
    if (params?.pet) q.set('pet', String(params.pet))
    if (params?.due) q.set('due', '1')
    const qs = q.toString()
    return _fetch(`/pets/treatments/${qs ? `?${qs}` : ''}`)
  },
  createPetTreatment: (data: TreatmentWrite): Promise<PetTreatment> =>
    _fetch('/pets/treatments/', { method: 'POST', body: JSON.stringify(data) }),
  updatePetTreatment: (id: number, data: TreatmentWrite): Promise<PetTreatment> =>
    _fetch(`/pets/treatments/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  completePetTreatment: (id: number): Promise<PetTreatment> =>
    _fetch(`/pets/treatments/${id}/complete/`, { method: 'POST' }),
  deletePetTreatment: (id: number): Promise<void> =>
    _fetch(`/pets/treatments/${id}/`, { method: 'DELETE' }),

  getPetAppointments: (params?: { pet?: number; upcoming?: boolean }): Promise<PetAppointment[]> => {
    const q = new URLSearchParams()
    if (params?.pet) q.set('pet', String(params.pet))
    if (params?.upcoming) q.set('upcoming', '1')
    const qs = q.toString()
    return _fetch(`/pets/appointments/${qs ? `?${qs}` : ''}`)
  },
  createPetAppointment: (data: AppointmentWrite): Promise<PetAppointment> =>
    _fetch('/pets/appointments/', { method: 'POST', body: JSON.stringify(data) }),
  updatePetAppointment: (id: number, data: AppointmentWrite): Promise<PetAppointment> =>
    _fetch(`/pets/appointments/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePetAppointment: (id: number): Promise<void> =>
    _fetch(`/pets/appointments/${id}/`, { method: 'DELETE' }),

  // --- Homestead (home / property hub) ---
  searchHomestead: (q: string): Promise<HomesteadSearchResults> =>
    _fetch(`/homestead/search/?q=${encodeURIComponent(q)}`),

  getProperties: (): Promise<Property[]> => _fetch('/homestead/properties/'),
  createProperty: (data: PropertyWrite): Promise<Property> =>
    _fetch('/homestead/properties/', { method: 'POST', body: JSON.stringify(data) }),
  updateProperty: (id: number, data: PropertyWrite): Promise<Property> =>
    _fetch(`/homestead/properties/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProperty: (id: number): Promise<void> =>
    _fetch(`/homestead/properties/${id}/`, { method: 'DELETE' }),

  getProviders: (): Promise<ServiceProvider[]> => _fetch('/homestead/providers/'),
  createProvider: (data: ProviderWrite): Promise<ServiceProvider> =>
    _fetch('/homestead/providers/', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider: (id: number, data: ProviderWrite): Promise<ServiceProvider> =>
    _fetch(`/homestead/providers/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProvider: (id: number): Promise<void> =>
    _fetch(`/homestead/providers/${id}/`, { method: 'DELETE' }),

  getAppliances: (expiring = false): Promise<Appliance[]> =>
    _fetch(`/homestead/appliances/${expiring ? '?expiring=1' : ''}`),
  createAppliance: (data: ApplianceWrite): Promise<Appliance> =>
    _fetch('/homestead/appliances/', { method: 'POST', body: JSON.stringify(data) }),
  updateAppliance: (id: number, data: ApplianceWrite): Promise<Appliance> =>
    _fetch(`/homestead/appliances/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAppliance: (id: number): Promise<void> =>
    _fetch(`/homestead/appliances/${id}/`, { method: 'DELETE' }),

  getMaintenance: (due = false): Promise<MaintenanceTask[]> =>
    _fetch(`/homestead/maintenance/${due ? '?due=1' : ''}`),
  createMaintenance: (data: MaintenanceWrite): Promise<MaintenanceTask> =>
    _fetch('/homestead/maintenance/', { method: 'POST', body: JSON.stringify(data) }),
  updateMaintenance: (id: number, data: MaintenanceWrite): Promise<MaintenanceTask> =>
    _fetch(`/homestead/maintenance/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  completeMaintenance: (id: number): Promise<MaintenanceTask> =>
    _fetch(`/homestead/maintenance/${id}/complete/`, { method: 'POST' }),
  trackMaintenanceCost: (id: number, data: { amount: string; category: string }): Promise<MaintenanceTask> =>
    _fetch(`/homestead/maintenance/${id}/track-cost/`, {
      method: 'POST', body: JSON.stringify(data),
    }),
  deleteMaintenance: (id: number): Promise<void> =>
    _fetch(`/homestead/maintenance/${id}/`, { method: 'DELETE' }),

  getPools: (activeOnly = false): Promise<Pool[]> =>
    _fetch(`/homestead/pools/${activeOnly ? '?active=1' : ''}`),
  createPool: (data: PoolWrite): Promise<Pool> =>
    _fetch('/homestead/pools/', { method: 'POST', body: JSON.stringify(data) }),
  updatePool: (id: number, data: PoolWrite): Promise<Pool> =>
    _fetch(`/homestead/pools/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePool: (id: number): Promise<void> =>
    _fetch(`/homestead/pools/${id}/`, { method: 'DELETE' }),
  getPoolStatus: (id: number): Promise<PoolStatus> =>
    _fetch(`/homestead/pools/${id}/status/`),
  applyPoolCareSchedule: (id: number): Promise<{ created: MaintenanceTask[] }> =>
    _fetch(`/homestead/pools/${id}/care-schedule/`, { method: 'POST' }),
  getWaterTests: (poolId: number): Promise<WaterTest[]> =>
    _fetch(`/homestead/pools/${poolId}/water-tests/`),
  logWaterTest: (poolId: number, data: WaterTestWrite): Promise<WaterTest> =>
    _fetch(`/homestead/pools/${poolId}/water-tests/`, { method: 'POST', body: JSON.stringify(data) }),
  deleteWaterTest: (poolId: number, testId: number): Promise<void> =>
    _fetch(`/homestead/pools/${poolId}/water-tests/${testId}/`, { method: 'DELETE' }),

  getImprovements: (open = false): Promise<Improvement[]> =>
    _fetch(`/homestead/improvements/${open ? '?open=1' : ''}`),
  createImprovement: (data: ImprovementWrite): Promise<Improvement> =>
    _fetch('/homestead/improvements/', { method: 'POST', body: JSON.stringify(data) }),
  updateImprovement: (id: number, data: ImprovementWrite): Promise<Improvement> =>
    _fetch(`/homestead/improvements/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteImprovement: (id: number): Promise<void> =>
    _fetch(`/homestead/improvements/${id}/`, { method: 'DELETE' }),

  getRooms: (): Promise<RoomListResponse> => _fetch('/homestead/rooms/'),
  getRoom: (id: number): Promise<RoomDetailResponse> => _fetch(`/homestead/rooms/${id}/`),
  createRoom: (data: RoomWrite): Promise<RoomArea> =>
    _fetch('/homestead/rooms/', { method: 'POST', body: JSON.stringify(data) }),
  updateRoom: (id: number, data: RoomWrite): Promise<RoomArea> =>
    _fetch(`/homestead/rooms/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRoom: (id: number): Promise<void> =>
    _fetch(`/homestead/rooms/${id}/`, { method: 'DELETE' }),
  createRoomItem: (roomId: number, data: RoomItemWrite): Promise<RoomPlanItem> =>
    _fetch(`/homestead/rooms/${roomId}/items/`, { method: 'POST', body: JSON.stringify(data) }),
  updateRoomItem: (roomId: number, itemId: number, data: RoomItemWrite): Promise<RoomPlanItem> =>
    _fetch(`/homestead/rooms/${roomId}/items/${itemId}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRoomItem: (roomId: number, itemId: number): Promise<void> =>
    _fetch(`/homestead/rooms/${roomId}/items/${itemId}/`, { method: 'DELETE' }),

  createRoomProduct: (roomId: number, itemId: number, data: RoomProductWrite): Promise<RoomPlanProduct> =>
    _fetch(`/homestead/rooms/${roomId}/items/${itemId}/products/`, { method: 'POST', body: JSON.stringify(data) }),
  updateRoomProduct: (roomId: number, itemId: number, productId: number, data: RoomProductWrite): Promise<RoomPlanProduct> =>
    _fetch(`/homestead/rooms/${roomId}/items/${itemId}/products/${productId}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRoomProduct: (roomId: number, itemId: number, productId: number): Promise<void> =>
    _fetch(`/homestead/rooms/${roomId}/items/${itemId}/products/${productId}/`, { method: 'DELETE' }),

  getInsurancePolicies: (active = false): Promise<InsurancePolicy[]> =>
    _fetch(`/homestead/insurance/${active ? '?active=1' : ''}`),
  createInsurancePolicy: (data: InsurancePolicyWrite): Promise<InsurancePolicy> =>
    _fetch('/homestead/insurance/', { method: 'POST', body: JSON.stringify(data) }),
  updateInsurancePolicy: (id: number, data: InsurancePolicyWrite): Promise<InsurancePolicy> =>
    _fetch(`/homestead/insurance/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteInsurancePolicy: (id: number): Promise<void> =>
    _fetch(`/homestead/insurance/${id}/`, { method: 'DELETE' }),

  getUtilityBills: (type?: UtilityType): Promise<UtilityBill[]> =>
    _fetch(`/homestead/utility-bills/${type ? `?type=${type}` : ''}`),
  createUtilityBill: (data: UtilityBillWrite): Promise<UtilityBill> =>
    _fetch('/homestead/utility-bills/', { method: 'POST', body: JSON.stringify(data) }),
  updateUtilityBill: (id: number, data: UtilityBillWrite): Promise<UtilityBill> =>
    _fetch(`/homestead/utility-bills/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUtilityBill: (id: number): Promise<void> =>
    _fetch(`/homestead/utility-bills/${id}/`, { method: 'DELETE' }),
  getUtilityUsage: (type?: UtilityType): Promise<UtilityUsageResponse> =>
    _fetch(`/homestead/utility-usage/${type ? `?type=${type}` : ''}`),

  getHouseholdCosts: (active = false): Promise<HouseholdCost[]> =>
    _fetch(`/homestead/costs/${active ? '?active=1' : ''}`),
  createHouseholdCost: (data: HouseholdCostWrite): Promise<HouseholdCost> =>
    _fetch('/homestead/costs/', { method: 'POST', body: JSON.stringify(data) }),
  updateHouseholdCost: (id: number, data: HouseholdCostWrite): Promise<HouseholdCost> =>
    _fetch(`/homestead/costs/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteHouseholdCost: (id: number): Promise<void> =>
    _fetch(`/homestead/costs/${id}/`, { method: 'DELETE' }),

  // --- Solace (finance) ---
  searchSolace: (q: string): Promise<SolaceSearchResults> =>
    _fetch(`/solace/search/?q=${encodeURIComponent(q)}`),
  getSolaceBootstrap: (): Promise<SolaceBootstrap> => _fetch('/solace/bootstrap/'),
  getSolacePlan: (date?: string): Promise<SolacePayCyclePlan> =>
    _fetch(`/solace/plan/${date ? `?date=${encodeURIComponent(date)}` : ''}`),
  generateSolacePlanChecklist: (date?: string): Promise<SolaceChecklistItem[]> =>
    _fetch(`/solace/plan/checklist/${date ? `?date=${encodeURIComponent(date)}` : ''}`, {
      method: 'POST',
    }),
  getSolaceSchedule: (start: string, end: string): Promise<SolaceSchedule> =>
    _fetch(`/solace/schedule/?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
  updateSolaceOccurrence: (
    id: number,
    action: 'paid' | 'unpaid' | 'skip',
  ): Promise<SolaceBillOccurrence> =>
    _fetch(`/solace/occurrences/${id}/${action}/`, { method: 'POST' }),
  getUpcomingSolaceOccurrences: (): Promise<SolaceBillOccurrence[]> =>
    _fetch('/solace/occurrences/upcoming/'),
  getSolaceBills: (params?: { upcoming?: boolean; unpaid?: boolean }): Promise<SolaceBill[]> => {
    const q = new URLSearchParams()
    if (params?.upcoming) q.set('upcoming', '1')
    if (params?.unpaid) q.set('unpaid', '1')
    const qs = q.toString()
    return _fetch(`/solace/bills/${qs ? `?${qs}` : ''}`)
  },
  createSolaceBill: (data: SolaceBillWrite): Promise<SolaceBill> =>
    _fetch('/solace/bills/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolaceBill: (id: number, data: SolaceBillWrite): Promise<SolaceBill> =>
    _fetch(`/solace/bills/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  getSolaceBillTimeline: (id: number): Promise<SolaceBillTimeline> =>
    _fetch(`/solace/bills/${id}/occurrences/`),
  markSolaceBillPaid: (id: number): Promise<SolaceBill> =>
    _fetch(`/solace/bills/${id}/paid/`, { method: 'POST' }),
  deleteSolaceBill: (id: number): Promise<void> =>
    _fetch(`/solace/bills/${id}/`, { method: 'DELETE' }),
  getSolacePaydays: (upcoming = false): Promise<SolacePayday[]> =>
    _fetch(`/solace/paydays/${upcoming ? '?upcoming=1' : ''}`),
  createSolacePayday: (data: SolacePaydayWrite): Promise<SolacePayday> =>
    _fetch('/solace/paydays/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolacePayday: (id: number, data: SolacePaydayWrite): Promise<SolacePayday> =>
    _fetch(`/solace/paydays/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSolacePayday: (id: number): Promise<void> =>
    _fetch(`/solace/paydays/${id}/`, { method: 'DELETE' }),
  getSolacePurchases: (open = false): Promise<SolacePurchase[]> =>
    _fetch(`/solace/purchases/${open ? '?open=1' : ''}`),
  createSolacePurchase: (data: SolacePurchaseWrite): Promise<SolacePurchase> =>
    _fetch('/solace/purchases/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolacePurchase: (id: number, data: SolacePurchaseWrite): Promise<SolacePurchase> =>
    _fetch(`/solace/purchases/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  addSolacePurchaseSavings: (id: number, amount: string): Promise<SolacePurchase> =>
    _fetch(`/solace/purchases/${id}/add-saved/`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }),
  deleteSolacePurchase: (id: number): Promise<void> =>
    _fetch(`/solace/purchases/${id}/`, { method: 'DELETE' }),
  getSolaceIncomeAllocations: (paydayId: number): Promise<SolaceIncomeAllocation[]> =>
    _fetch(`/solace/paydays/${paydayId}/allocations/`),
  setSolaceIncomeAllocations: (paydayId: number, lines: SolaceIncomeAllocationWrite[]): Promise<SolaceIncomeAllocation[]> =>
    _fetch(`/solace/paydays/${paydayId}/allocations/`, { method: 'PUT', body: JSON.stringify(lines) }),

  getSolaceCycleHistory: (): Promise<SolaceCycleHistoryRow[]> => _fetch('/solace/cycle-history/'),
  getSolaceAnnualSummary: (yearType: 'calendar' | 'financial' = 'calendar'): Promise<SolaceAnnualSummary> =>
    _fetch(`/solace/annual-summary/?year_type=${yearType}`),

  getSolaceNow: (): Promise<SolaceNow> => _fetch('/solace/now/'),
  getSolaceBucketEntries: (bucketId: number): Promise<SolaceBucketEntry[]> =>
    _fetch(`/solace/buckets/${bucketId}/entries/`),
  addSolaceBucketEntry: (bucketId: number, data: SolaceBucketEntryWrite): Promise<SolaceBucketEntry> =>
    _fetch(`/solace/buckets/${bucketId}/entries/`, { method: 'POST', body: JSON.stringify(data) }),
  deleteSolaceBucketEntry: (bucketId: number, entryId: number): Promise<void> =>
    _fetch(`/solace/buckets/${bucketId}/entries/${entryId}/`, { method: 'DELETE' }),

  getSolaceBuckets: (): Promise<SolaceBucket[]> => _fetch('/solace/buckets/'),
  createSolaceBucket: (data: SolaceBucketWrite): Promise<SolaceBucket> =>
    _fetch('/solace/buckets/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolaceBucket: (id: number, data: SolaceBucketWrite): Promise<SolaceBucket> =>
    _fetch(`/solace/buckets/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSolaceBucket: (id: number): Promise<void> =>
    _fetch(`/solace/buckets/${id}/`, { method: 'DELETE' }),
  getSolaceChecklist: (options: {
    incomplete?: boolean
    latest?: boolean
    date?: string
  } = {}): Promise<SolaceChecklistItem[]> => {
    const query = new URLSearchParams()
    if (options.incomplete) query.set('incomplete', '1')
    if (options.latest !== false) query.set('latest', '1')
    if (options.date) query.set('date', options.date)
    return _fetch(`/solace/checklist/${query.size ? `?${query}` : ''}`)
  },
  createSolaceChecklistItem: (data: SolaceChecklistWrite): Promise<SolaceChecklistItem> =>
    _fetch('/solace/checklist/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolaceChecklistItem: (id: number, data: SolaceChecklistWrite): Promise<SolaceChecklistItem> =>
    _fetch(`/solace/checklist/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSolaceChecklistItem: (id: number): Promise<void> =>
    _fetch(`/solace/checklist/${id}/`, { method: 'DELETE' }),
  getSolaceSettings: (): Promise<SolaceSettings> => _fetch('/solace/settings/'),
  updateSolaceSettings: (data: SolaceSettingsWrite): Promise<SolaceSettings> =>
    _fetch('/solace/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  getSolaceCategories: (): Promise<SolaceCategory[]> => _fetch('/solace/categories/'),
  createSolaceCategory: (data: SolaceCategoryWrite): Promise<SolaceCategory> =>
    _fetch('/solace/categories/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolaceCategory: (id: number, data: SolaceCategoryWrite): Promise<SolaceCategory> =>
    _fetch(`/solace/categories/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSolaceCategory: (id: number): Promise<void> =>
    _fetch(`/solace/categories/${id}/`, { method: 'DELETE' }),
  getSolaceBalances: (): Promise<SolaceBalanceSnapshot[]> => _fetch('/solace/balances/'),
  createSolaceBalance: (data: SolaceBalanceWrite): Promise<SolaceBalanceSnapshot> =>
    _fetch('/solace/balances/', { method: 'POST', body: JSON.stringify(data) }),
  updateSolaceBalance: (id: number, data: SolaceBalanceWrite): Promise<SolaceBalanceSnapshot> =>
    _fetch(`/solace/balances/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSolaceBalance: (id: number): Promise<void> =>
    _fetch(`/solace/balances/${id}/`, { method: 'DELETE' }),
  getSolaceChecklistPreferences: (): Promise<SolaceChecklistPreference[]> =>
    _fetch('/solace/checklist/preferences/'),
  setSolaceChecklistPreference: (data: {
    source_key: string; label: string; is_hidden: boolean; reason?: string
  }): Promise<SolaceChecklistPreference> =>
    _fetch('/solace/checklist/preferences/', { method: 'POST', body: JSON.stringify(data) }),
  getSolaceCloseout: (date?: string): Promise<SolaceCloseoutResponse> =>
    _fetch(`/solace/closeout/${date ? `?date=${encodeURIComponent(date)}` : ''}`),
  getSolaceForecast: (months = 12, date?: string): Promise<SolaceBalanceForecast> => {
    const query = new URLSearchParams({ months: String(months) })
    if (date) query.set('date', date)
    return _fetch(`/solace/forecast/?${query}`)
  },
  setSolaceCloseout: (
    action: 'close' | 'reopen',
    notes = '',
    date?: string,
  ): Promise<SolaceCycleCloseout> =>
    _fetch(`/solace/closeout/${date ? `?date=${encodeURIComponent(date)}` : ''}`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    }),
  getSolaceHealth: (): Promise<SolaceHealth> => _fetch('/solace/health/'),
  getSolaceCategoryReport: (activeOnly = true, includedOnly = false): Promise<SolaceCategoryReport> => {
    const query = new URLSearchParams({
      active: activeOnly ? '1' : '0',
      included: includedOnly ? '1' : '0',
    })
    return _fetch(`/solace/reports/categories/?${query}`)
  },
  previewSolaceBillImport: (file: File): Promise<SolaceBillImportPreview> => {
    const data = new FormData()
    data.append('file', file)
    return _fetchRaw('/solace/import/bills/preview/', { method: 'POST', body: data })
  },
  confirmSolaceBillImport: (): Promise<{ imported_count: number; skipped_count: number }> =>
    _fetch('/solace/import/bills/confirm/', { method: 'POST' }),
  cancelSolaceBillImport: (): Promise<void> =>
    _fetch('/solace/import/bills/cancel/', { method: 'POST' }),

  // --- Fitness & training ---
  getFitnessExercises: (query = '', type = '', muscleGroup = ''): Promise<FitnessExercise[]> => {
    const params = new URLSearchParams()
    if (query) params.set('q', query)
    if (type) params.set('type', type)
    if (muscleGroup) params.set('muscle_group', muscleGroup)
    return _fetch(`/fitness/exercises/${params.size ? `?${params}` : ''}`)
  },
  createFitnessExercise: (data: Partial<FitnessExercise>): Promise<FitnessExercise> =>
    _fetch('/fitness/exercises/', { method: 'POST', body: JSON.stringify(data) }),
  updateFitnessExercise: (id: number, data: Partial<FitnessExercise>): Promise<FitnessExercise> =>
    _fetch(`/fitness/exercises/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteFitnessExercise: (id: number): Promise<void> =>
    _fetch(`/fitness/exercises/${id}/`, { method: 'DELETE' }),
  getFitnessPrograms: (): Promise<FitnessProgram[]> => _fetch('/fitness/programs/'),
  createFitnessProgram: (data: FitnessProgramWrite): Promise<FitnessProgram> =>
    _fetch('/fitness/programs/', { method: 'POST', body: JSON.stringify(data) }),
  updateFitnessProgram: (id: number, data: FitnessProgramWrite): Promise<FitnessProgram> =>
    _fetch(`/fitness/programs/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteFitnessProgram: (id: number): Promise<void> =>
    _fetch(`/fitness/programs/${id}/`, { method: 'DELETE' }),
  getFitnessSessions: (personId?: number, status?: string): Promise<FitnessSession[]> => {
    const params = new URLSearchParams()
    if (personId) params.set('person', String(personId))
    if (status) params.set('status', status)
    return _fetch(`/fitness/sessions/${params.size ? `?${params}` : ''}`)
  },
  startFitnessSession: (data: { person_id: number; workout_id?: number; name?: string; visibility?: 'private' | 'household' }): Promise<FitnessSession> =>
    _fetch('/fitness/sessions/start/', { method: 'POST', body: JSON.stringify(data) }),
  addFitnessSessionExercise: (sessionId: number, data: { exercise_id: number; target_sets: number; notes?: string }): Promise<FitnessSessionExercise> =>
    _fetch(`/fitness/sessions/${sessionId}/exercises/`, { method: 'POST', body: JSON.stringify(data) }),
  dropFitnessSessionExercise: (entryId: number): Promise<FitnessSessionExercise> =>
    _fetch(`/fitness/session-exercises/${entryId}/drop/`, { method: 'POST' }),
  addFitnessSessionSet: (entryId: number): Promise<FitnessSessionSet> =>
    _fetch(`/fitness/session-exercises/${entryId}/sets/`, { method: 'POST' }),
  updateFitnessSessionSet: (setId: number, data: Partial<FitnessSessionSet>): Promise<FitnessSessionSet> =>
    _fetch(`/fitness/session-sets/${setId}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  finishFitnessSession: (sessionId: number, notes = ''): Promise<FitnessSession> =>
    _fetch(`/fitness/sessions/${sessionId}/finish/`, { method: 'POST', body: JSON.stringify({ notes }) }),
  abandonFitnessSession: (sessionId: number): Promise<FitnessSession> =>
    _fetch(`/fitness/sessions/${sessionId}/abandon/`, { method: 'POST' }),
  getFitnessRecords: (personId?: number): Promise<FitnessRecord[]> =>
    _fetch(`/fitness/records/${personId ? `?person=${personId}` : ''}`),

  // --- Books ---
  getBooksUsers: (): Promise<BooksUser[]> => _fetch('/books/users/'),
  searchBooks: (q: string): Promise<Book[]> => _fetch(`/books/books/${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  createBook: (data: BookWrite): Promise<Book> =>
    _fetch('/books/books/', { method: 'POST', body: JSON.stringify(data) }),
  updateBook: (id: number, data: BookWrite): Promise<Book> =>
    _fetch(`/books/books/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteBook: (id: number): Promise<void> =>
    _fetch(`/books/books/${id}/`, { method: 'DELETE' }),
  upsertBookRating: (data: { book_id: number; rating?: number | null; notes?: string }): Promise<BookRating> =>
    _fetch('/books/ratings/', { method: 'POST', body: JSON.stringify(data) }),
  getPersonalBooks: (includeClubs = true): Promise<{ personal: PersonalBookEntry[]; club: ClubBookEntry[] }> =>
    _fetch(`/books/personal/${includeClubs ? '' : '?include_clubs=0'}`),
  createPersonalBook: (data: ShelfWrite): Promise<PersonalBookEntry> =>
    _fetch('/books/personal/', { method: 'POST', body: JSON.stringify(data) }),
  updatePersonalBook: (id: number, data: Partial<{ status: BookShelfStatus; position: number }>): Promise<PersonalBookEntry> =>
    _fetch(`/books/personal/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePersonalBook: (id: number): Promise<void> =>
    _fetch(`/books/personal/${id}/`, { method: 'DELETE' }),
  getBookClubs: (): Promise<BookClub[]> => _fetch('/books/clubs/'),
  createBookClub: (data: Partial<{ name: string; colour: string; description: string }>): Promise<BookClub> =>
    _fetch('/books/clubs/', { method: 'POST', body: JSON.stringify(data) }),
  updateBookClub: (id: number, data: Partial<{ name: string; colour: string; description: string }>): Promise<BookClub> =>
    _fetch(`/books/clubs/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteBookClub: (id: number): Promise<void> =>
    _fetch(`/books/clubs/${id}/`, { method: 'DELETE' }),
  addBookClubMember: (clubId: number, userId: number): Promise<BookClub> =>
    _fetch(`/books/clubs/${clubId}/members/`, { method: 'POST', body: JSON.stringify({ user_id: userId }) }),
  removeBookClubMember: (clubId: number, membershipId: number): Promise<void> =>
    _fetch(`/books/clubs/${clubId}/members/${membershipId}/`, { method: 'DELETE' }),
  getClubBooks: (clubId: number, status?: BookShelfStatus): Promise<ClubBookEntry[]> =>
    _fetch(`/books/clubs/${clubId}/books/${status ? `?status=${status}` : ''}`),
  createClubBook: (clubId: number, data: ShelfWrite): Promise<ClubBookEntry> =>
    _fetch(`/books/clubs/${clubId}/books/`, { method: 'POST', body: JSON.stringify(data) }),
  updateClubBook: (clubId: number, entryId: number, data: Partial<{ status: BookShelfStatus; position: number }>): Promise<ClubBookEntry[]> =>
    _fetch(`/books/clubs/${clubId}/books/${entryId}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteClubBook: (clubId: number, entryId: number): Promise<void> =>
    _fetch(`/books/clubs/${clubId}/books/${entryId}/`, { method: 'DELETE' }),
  getClubQueue: (clubId: number): Promise<ClubQueueItem[]> =>
    _fetch(`/books/clubs/${clubId}/queue/`),
  addClubQueueItem: (clubId: number, clubBookId: number, position?: number): Promise<ClubQueueItem> =>
    _fetch(`/books/clubs/${clubId}/queue/`, { method: 'POST', body: JSON.stringify({ club_book_id: clubBookId, position }) }),
  updateClubQueueItem: (clubId: number, itemId: number, position: number): Promise<ClubQueueItem> =>
    _fetch(`/books/clubs/${clubId}/queue/${itemId}/`, { method: 'PATCH', body: JSON.stringify({ position }) }),
  deleteClubQueueItem: (clubId: number, itemId: number): Promise<void> =>
    _fetch(`/books/clubs/${clubId}/queue/${itemId}/`, { method: 'DELETE' }),

  // --- Notifications ---
  getNotifications: (unreadOnly?: boolean): Promise<NotificationList> =>
    _fetch(`/notifications/${unreadOnly ? '?unread=1' : ''}`),
  markNotificationRead: (id: number): Promise<unknown> =>
    _fetch(`/notifications/${id}/read/`, { method: 'POST' }),
  markAllNotificationsRead: (throughId?: number): Promise<unknown> =>
    _fetch('/notifications/read-all/', {
      method: 'POST', body: JSON.stringify(throughId ? { through_id: throughId } : {}),
    }),
  getNotificationPreferences: (): Promise<NotificationPreference[]> =>
    _fetch('/notifications/preferences/'),
  updateNotificationPreferences: (rows: Partial<NotificationPreference>[]): Promise<NotificationPreference[]> =>
    _fetch('/notifications/preferences/', { method: 'PATCH', body: JSON.stringify(rows) }),
  getNotificationSettings: (): Promise<UserNotificationSettings> =>
    _fetch('/notifications/settings/'),
  updateNotificationSettings: (data: Partial<UserNotificationSettings>): Promise<UserNotificationSettings> =>
    _fetch('/notifications/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  getVapidPublicKey: (): Promise<{ public_key: string }> =>
    _fetch('/notifications/vapid-public-key/'),
  getPushDevices: (): Promise<PushDevice[]> => _fetch('/notifications/devices/'),
  getCurrentPushDevice: (endpoint: string): Promise<{ device_id: number | null }> =>
    _fetch('/notifications/devices/current/', { method: 'POST', body: JSON.stringify({ endpoint }) }),
  registerPushDevice: (data: { endpoint: string; keys: { p256dh: string; auth: string }; label?: string }): Promise<PushDevice> =>
    _fetch('/notifications/devices/', { method: 'POST', body: JSON.stringify(data) }),
  renamePushDevice: (id: number, label: string): Promise<PushDevice> =>
    _fetch(`/notifications/devices/${id}/`, { method: 'PATCH', body: JSON.stringify({ label }) }),
  unregisterPushDevice: (id: number): Promise<void> =>
    _fetch(`/notifications/devices/${id}/`, { method: 'DELETE' }),
  getHouseholdPushDevices: (): Promise<HouseholdPushDeviceGroup[]> =>
    _fetch('/notifications/household-devices/'),
  testPushDevice: (id: number): Promise<{ delivered: boolean }> =>
    _fetch(`/notifications/devices/${id}/test/`, { method: 'POST' }),
}
