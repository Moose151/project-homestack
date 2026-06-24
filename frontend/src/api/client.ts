import type {
  AtlasList, AtlasListItem, AtlasNote, AtlasReminder,
  AuthUser, CalendarEvent, HubResponse, KioskUser,
  KioskMeridian, MeridianPointsResponse, MeridianReward,
  MeridianRewardRequest, MeridianTask,
} from './types'

import { pushToast } from '../components/Toast'

const BASE = '/api/v1'

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

interface FetchOpts {
  // Skip the automatic error toast (for flows that show their own message, e.g. auth).
  silent?: boolean
}

// Pull a human-friendly message out of a DRF error response.
async function _errorMessage(res: Response): Promise<string> {
  try {
    const data = await res.clone().json()
    if (typeof data === 'string') return data
    if (data?.detail) return String(data.detail)
    const firstKey = data && Object.keys(data)[0]
    if (firstKey) {
      const val = data[firstKey]
      const msg = Array.isArray(val) ? val[0] : val
      return firstKey === 'detail' || /^\d/.test(firstKey) ? String(msg) : `${firstKey}: ${msg}`
    }
  } catch {
    /* response body was not JSON */
  }
  if (res.status === 403) return 'You don’t have permission to do that.'
  if (res.status === 401) return 'Please sign in again.'
  return `Something went wrong (${res.status}).`
}

async function _fetch<T>(path: string, init?: RequestInit, opts?: FetchOpts): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase()
  // Django session auth (DRF) enforces CSRF on unsafe methods; send the token the
  // server seeded via the csrftoken cookie (set on /auth/me/ and /auth/kiosk-users/).
  const csrfHeader: Record<string, string> =
    SAFE_METHODS.has(method) ? {} : { 'X-CSRFToken': getCookie('csrftoken') ?? '' }

  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...csrfHeader, ...init?.headers },
      ...init,
    })
  } catch {
    // Network/connection failure — never silent, the user needs to know.
    const msg = 'Network error — could not reach the server.'
    pushToast(msg, 'error')
    throw new Error(msg)
  }
  if (!res.ok) {
    const message = await _errorMessage(res)
    if (!opts?.silent) pushToast(message, 'error')
    throw new Error(message)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // --- Auth --- (silent: these flows surface their own inline messages)
  getKioskUsers: (): Promise<KioskUser[]> => _fetch('/auth/kiosk-users/'),
  pinLogin: (username: string, pin: string): Promise<AuthUser> =>
    _fetch('/auth/pin-login/', { method: 'POST', body: JSON.stringify({ username, pin }) }, { silent: true }),
  passwordLogin: (username: string, password: string): Promise<AuthUser> =>
    _fetch('/auth/password-login/', { method: 'POST', body: JSON.stringify({ username, password }) }, { silent: true }),
  logout: (): Promise<void> => _fetch('/auth/logout/', { method: 'POST' }),
  me: (): Promise<AuthUser> => _fetch('/auth/me/', undefined, { silent: true }),
  reauth: (password: string): Promise<void> =>
    _fetch('/auth/reauth/', { method: 'POST', body: JSON.stringify({ password }) }, { silent: true }),

  // --- Hub ---
  hub: (): Promise<HubResponse> => _fetch('/hub/'),
  kioskHub: (): Promise<HubResponse> => _fetch('/hub/kiosk/'),

  // --- Atlas lists ---
  getLists: (): Promise<AtlasList[]> => _fetch('/atlas/lists/'),
  getList: (id: number): Promise<AtlasList> => _fetch(`/atlas/lists/${id}/`),
  createList: (data: { title: string; list_type: string; visibility?: string }): Promise<AtlasList> =>
    _fetch('/atlas/lists/', { method: 'POST', body: JSON.stringify(data) }),
  deleteList: (id: number): Promise<void> => _fetch(`/atlas/lists/${id}/`, { method: 'DELETE' }),

  // --- Atlas list items ---
  createItem: (listId: number, data: { title: string }): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/`, { method: 'POST', body: JSON.stringify(data) }),
  completeItem: (listId: number, itemId: number): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/complete/`, { method: 'POST' }),
  uncompleteItem: (listId: number, itemId: number): Promise<AtlasListItem> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/uncomplete/`, { method: 'POST' }),
  deleteItem: (listId: number, itemId: number): Promise<void> =>
    _fetch(`/atlas/lists/${listId}/items/${itemId}/`, { method: 'DELETE' }),

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
  getEvents: (): Promise<CalendarEvent[]> => _fetch('/calendar/events/'),

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

  // --- Meridian: points ---
  getMeridianPoints: (): Promise<MeridianPointsResponse> => _fetch('/meridian/points/'),

  // --- Meridian: rewards ---
  getMeridianRewards: (activeOnly?: boolean): Promise<MeridianReward[]> =>
    _fetch(`/meridian/rewards/${activeOnly ? '?active=1' : ''}`),
  createMeridianReward: (data: {
    name: string; cost_points: number; description?: string
  }): Promise<MeridianReward> =>
    _fetch('/meridian/rewards/', { method: 'POST', body: JSON.stringify(data) }),
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

  // --- Meridian: kiosk ---
  kioskMeridian: (): Promise<KioskMeridian> => _fetch('/kiosk/meridian/'),
}
