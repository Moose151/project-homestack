import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  AssessmentPriority, AssessmentStatus, AssessmentType,
  EducationAssessment, EducationClassSession, EducationCourse,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { DateTimeField } from '../../../components/DateTimeField'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const inputCls =
  'w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink ' +
  'placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]'

const TYPE_LABELS: Record<AssessmentType, string> = {
  homework: 'Homework', assignment: 'Assignment', exam: 'Exam', quiz: 'Quiz',
  reading: 'Reading', project: 'Project', other: 'Other',
}
const STATUS_LABELS: Record<AssessmentStatus, string> = {
  todo: 'To do', in_progress: 'In progress', submitted: 'Submitted', done: 'Done',
}
const PRIORITY_TONE: Record<AssessmentPriority, string> = {
  high: 'bg-danger-soft text-danger', medium: 'bg-primary-soft text-primary',
  low: 'bg-sunken text-muted-strong',
}
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function dueLabel(iso: string | null, allDay = false) {
  if (!iso) return null
  const d = new Date(iso)
  const diff = Math.round((d.getTime() - Date.now()) / 86400000)
  const time = allDay ? '' : ` · ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
  if (diff < 0) return { text: `${Math.abs(diff)}d overdue`, tone: 'bg-danger-soft text-danger' }
  if (diff === 0) return { text: `Today${time}`, tone: 'bg-primary-soft text-primary' }
  if (diff === 1) return { text: `Tomorrow${time}`, tone: 'bg-sunken text-muted-strong' }
  return {
    text: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    tone: 'bg-sunken text-muted-strong',
  }
}

// datetime-local -> ISO helper (local time in the input, ISO on the wire)
function fromInputValue(v: string): string | null {
  return v ? new Date(v).toISOString() : null
}
function calendarDayHref(iso: string | null) {
  return iso ? `/calendar?date=${new Date(iso).toISOString().slice(0, 10)}` : '/calendar'
}

type Tab = 'assignments' | 'courses' | 'timetable'

// ===========================================================================
// Assignments
// ===========================================================================

function AssignmentForm({ courses, onCreated, onError }: {
  courses: EducationCourse[]
  onCreated: (a: EducationAssessment) => void
  onError: (m: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [type, setType] = useState<AssessmentType>('assignment')
  const [courseId, setCourseId] = useState('')
  const [due, setDue] = useState<string | null>(null)
  const [dueAllDay, setDueAllDay] = useState(true)
  const [priority, setPriority] = useState<AssessmentPriority>('medium')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const a = await api.createAssessment({
        title: title.trim(), assessment_type: type, priority,
        course_id: courseId ? Number(courseId) : null,
        due_at: due, is_all_day: dueAllDay,
      })
      onCreated(a)
      setTitle(''); setDue(null); setDueAllDay(true); setCourseId(''); setType('assignment'); setPriority('medium')
      setOpen(false)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  if (!open) {
    return <Button variant="secondary" onClick={() => setOpen(true)}>+ Add assignment</Button>
  }
  return (
    <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
      <input autoFocus className={inputCls} placeholder="Assignment title" value={title}
        onChange={e => setTitle(e.target.value)} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <select className={inputCls} value={type} onChange={e => setType(e.target.value as AssessmentType)}>
          {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className={inputCls} value={courseId} onChange={e => setCourseId(e.target.value)}>
          <option value="">No course</option>
          {courses.map(c => <option key={c.id} value={c.id}>{c.code || c.name}</option>)}
        </select>
        <select className={inputCls} value={priority} onChange={e => setPriority(e.target.value as AssessmentPriority)}>
          <option value="low">Low priority</option>
          <option value="medium">Medium priority</option>
          <option value="high">High priority</option>
        </select>
      </div>
      <div>
        <div className="text-xs text-muted-strong mb-1">Due</div>
        <DateTimeField value={due} allDay={dueAllDay}
          onChange={({ value, allDay }) => { setDue(value); setDueAllDay(allDay) }} />
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={busy}>Add</Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </form>
  )
}

function AssignmentRow({ a, onChange, onDelete, onError }: {
  a: EducationAssessment
  onChange: (a: EducationAssessment) => void
  onDelete: (id: number) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const due = dueLabel(a.due_at, a.is_all_day)

  const setStatus = async (status: AssessmentStatus) => {
    setBusy(true)
    try { onChange(await api.updateAssessment(a.id, { status })) }
    catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!confirm('Delete this assignment?')) return
    try { await api.deleteAssessment(a.id); onDelete(a.id) } catch (e) { onError(errMsg(e)) }
  }

  return (
    <li className="flex items-start gap-3 py-3 group">
      <button
        onClick={() => setStatus(a.is_complete ? 'todo' : 'done')}
        disabled={busy}
        className={`w-6 h-6 mt-0.5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${
          a.is_complete ? 'bg-success border-success text-white' : 'border-line-strong hover:border-success'
        }`}
        aria-label={a.is_complete ? 'Mark not done' : 'Mark done'}
      >
        {a.is_complete && <span className="text-xs">✓</span>}
      </button>

      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${a.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
          {a.title}
        </div>
        <div className="flex flex-wrap items-center gap-1.5 mt-1">
          <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">{TYPE_LABELS[a.assessment_type]}</span>
          {(a.course_code || a.course_name) && (
            <span className="text-xs text-muted">{a.course_code || a.course_name}</span>
          )}
          {!a.is_complete && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_TONE[a.priority]}`}>{a.priority}</span>}
          {due && (
            <Link to={calendarDayHref(a.due_at)} className={`text-xs px-2 py-0.5 rounded-full font-medium ${due.tone}`}>{due.text}</Link>
          )}
        </div>
      </div>

      <select
        value={a.status}
        onChange={e => setStatus(e.target.value as AssessmentStatus)}
        disabled={busy}
        className="text-xs rounded-lg border border-line bg-surface px-2 py-1 text-muted-strong flex-shrink-0"
      >
        {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      <button onClick={remove} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none flex-shrink-0" aria-label="Delete">×</button>
    </li>
  )
}

function AssignmentsTab({ courses, onError }: { courses: EducationCourse[]; onError: (m: string) => void }) {
  const [assessments, setAssessments] = useState<EducationAssessment[]>([])
  const [showDone, setShowDone] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAssessments(showDone ? undefined : { open: true })
      .then(setAssessments).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [showDone, onError])

  const upsert = (a: EducationAssessment) =>
    setAssessments(prev => {
      const next = prev.some(x => x.id === a.id) ? prev.map(x => x.id === a.id ? a : x) : [...prev, a]
      if (!showDone && a.is_complete) return next.filter(x => x.id !== a.id)
      return next
    })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <AssignmentForm courses={courses} onCreated={upsert} onError={onError} />
        <label className="flex items-center gap-2 text-sm text-muted-strong">
          <input type="checkbox" checked={showDone} onChange={e => setShowDone(e.target.checked)} />
          Show completed
        </label>
      </div>
      <Card>
        {loading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : assessments.length === 0 ? (
          <p className="text-sm text-muted py-4 text-center">Nothing due. Add your first assignment above.</p>
        ) : (
          <ul className="divide-y divide-line">
            {assessments.map(a => (
              <AssignmentRow key={a.id} a={a} onChange={upsert} onDelete={id => setAssessments(prev => prev.filter(x => x.id !== id))} onError={onError} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

// ===========================================================================
// Courses
// ===========================================================================

function CoursesTab({ courses, reload, onError }: {
  courses: EducationCourse[]; reload: () => void; onError: (m: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [teacher, setTeacher] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      await api.createCourse({ name: name.trim(), code: code.trim(), teacher: teacher.trim() })
      setName(''); setCode(''); setTeacher(''); setOpen(false); reload()
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async (c: EducationCourse) => {
    if (!confirm(`Delete "${c.name}"? Its assignments stay but lose their course link.`)) return
    try { await api.deleteCourse(c.id); reload() } catch (e) { onError(errMsg(e)) }
  }

  return (
    <div className="space-y-4">
      {open ? (
        <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
          <input autoFocus className={inputCls} placeholder="Course/subject name" value={name} onChange={e => setName(e.target.value)} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input className={inputCls} placeholder="Code (e.g. COMP2001)" value={code} onChange={e => setCode(e.target.value)} />
            <input className={inputCls} placeholder="Lecturer / teacher" value={teacher} onChange={e => setTeacher(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>Add course</Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </form>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>+ Add course</Button>
      )}

      {courses.length === 0 ? (
        <Card><p className="text-sm text-muted py-4 text-center">No courses yet.</p></Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {courses.map(c => (
            <div key={c.id} className="bg-surface rounded-2xl border border-line p-4 group">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-semibold text-ink truncate">{c.name}</div>
                  {c.code && <div className="text-xs text-primary font-medium">{c.code}</div>}
                </div>
                <button onClick={() => remove(c)} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none" aria-label="Delete">×</button>
              </div>
              {c.teacher && <div className="text-sm text-muted mt-2">{c.teacher}</div>}
              {c.institution_name && <div className="text-xs text-muted mt-1">{c.institution_name}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Timetable
// ===========================================================================

function TimetableTab({ courses, onError }: { courses: EducationCourse[]; onError: (m: string) => void }) {
  const [sessions, setSessions] = useState<EducationClassSession[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('Lecture')
  const [courseId, setCourseId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [location, setLocation] = useState('')
  const [weekly, setWeekly] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getClassSessions().then(setSessions).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [onError])

  const grouped = useMemo(() => {
    const by: Record<number, EducationClassSession[]> = {}
    for (const s of sessions) {
      const wd = new Date(s.start_at).getDay()
      ;(by[wd] ??= []).push(s)
    }
    for (const k of Object.keys(by)) {
      by[+k].sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    }
    return by
  }, [sessions])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!start) { onError('A start time is required.'); return }
    setBusy(true)
    try {
      const s = await api.createClassSession({
        title: title.trim(), course_id: courseId ? Number(courseId) : null,
        location: location.trim(), start_at: fromInputValue(start)!, end_at: fromInputValue(end),
        recurrence_rule: weekly ? 'FREQ=WEEKLY' : '',
      })
      setSessions(prev => [...prev, s])
      setStart(''); setEnd(''); setLocation(''); setCourseId(''); setTitle('Lecture'); setOpen(false)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async (s: EducationClassSession) => {
    if (!confirm('Delete this class from your timetable?')) return
    try { await api.deleteClassSession(s.id); setSessions(prev => prev.filter(x => x.id !== s.id)) }
    catch (e) { onError(errMsg(e)) }
  }

  return (
    <div className="space-y-4">
      {open ? (
        <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input autoFocus className={inputCls} placeholder="Label (e.g. Lecture, Tutorial)" value={title} onChange={e => setTitle(e.target.value)} />
            <select className={inputCls} value={courseId} onChange={e => setCourseId(e.target.value)}>
              <option value="">No course</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.code || c.name}</option>)}
            </select>
            <label className="text-xs text-muted-strong flex flex-col gap-1">Starts
              <input type="datetime-local" className={inputCls} value={start} onChange={e => setStart(e.target.value)} />
            </label>
            <label className="text-xs text-muted-strong flex flex-col gap-1">Ends
              <input type="datetime-local" className={inputCls} value={end} onChange={e => setEnd(e.target.value)} />
            </label>
            <input className={inputCls} placeholder="Location (room / building)" value={location} onChange={e => setLocation(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-strong">
            <input type="checkbox" checked={weekly} onChange={e => setWeekly(e.target.checked)} />
            Repeats weekly
          </label>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>Add class</Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </form>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>+ Add class</Button>
      )}

      {loading ? (
        <Card><p className="text-sm text-muted">Loading…</p></Card>
      ) : sessions.length === 0 ? (
        <Card><p className="text-sm text-muted py-4 text-center">No classes yet. Add your weekly lectures and tutorials.</p></Card>
      ) : (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5, 6, 0].filter(wd => grouped[wd]?.length).map(wd => (
            <Card key={wd} title={WEEKDAYS[wd] === 'Sun' ? 'Sunday' : ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][wd]}>
              <ul className="divide-y divide-line -mt-1">
                {grouped[wd].map(s => {
                  const t0 = new Date(s.start_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
                  const t1 = s.end_at ? new Date(s.end_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : null
                  return (
                    <li key={s.id} className="flex items-center gap-3 py-2.5 group">
                      <div className="text-sm font-medium text-primary w-28 flex-shrink-0">{t0}{t1 ? `–${t1}` : ''}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-ink truncate">{s.display_title}</div>
                        {s.location && <div className="text-xs text-muted">{s.location}</div>}
                      </div>
                      {s.recurrence_rule && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong flex-shrink-0">Weekly</span>}
                      <button onClick={() => remove(s)} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none flex-shrink-0" aria-label="Delete">×</button>
                    </li>
                  )
                })}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Page
// ===========================================================================

const TABS: { key: Tab; label: string }[] = [
  { key: 'assignments', label: 'Assignments' },
  { key: 'courses', label: 'Courses' },
  { key: 'timetable', label: 'Timetable' },
]

export function EducationPage() {
  const [tab, setTab] = useState<Tab>('assignments')
  const [courses, setCourses] = useState<EducationCourse[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadCourses = () => api.getCourses().then(setCourses).catch(e => setError(errMsg(e)))
  useEffect(() => { loadCourses() }, [])

  return (
    <div className="space-y-5 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">Education</h1>
        <p className="text-sm text-muted">Your courses, deadlines and weekly timetable.</p>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="flex gap-1 bg-sunken rounded-2xl p-1 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 min-w-[110px] px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
              tab === t.key ? 'bg-surface text-primary shadow-soft' : 'text-muted-strong hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'assignments' && <AssignmentsTab courses={courses} onError={setError} />}
      {tab === 'courses' && <CoursesTab courses={courses} reload={loadCourses} onError={setError} />}
      {tab === 'timetable' && <TimetableTab courses={courses} onError={setError} />}
    </div>
  )
}
